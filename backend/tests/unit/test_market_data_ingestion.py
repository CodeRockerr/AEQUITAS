"""
AEQUITAS - Unit tests for market data validation layer and auto-ingest.

The Pydantic validation model tests are pure logic - no database, no
yFinance calls. The ensure_min_bars/ensure_company_info tests use a
fake AsyncSession (this repo has no test-DB fixture) and monkeypatch
the actual yFinance-calling functions, matching test_price_stream.py's
pattern of mocking at the module's own async boundaries.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.data.ingestion.market_data import (
    CompanyInfoRow,
    OHLCVRow,
    ensure_company_info,
    ensure_min_bars,
)


@pytest.mark.unit
def test_ohlcv_row_valid() -> None:
    """A well-formed OHLCV row should validate successfully."""
    row = OHLCVRow(
        time=datetime.now(UTC),
        ticker="aapl",  # lowercase - should be normalised
        interval="1d",
        open=Decimal("150.00"),
        high=Decimal("155.00"),
        low=Decimal("149.00"),
        close=Decimal("153.00"),
        volume=50_000_000,
    )
    assert row.ticker == "AAPL"  # normalised to uppercase
    assert row.open == Decimal("150.00")


@pytest.mark.unit
def test_ohlcv_row_normalises_ticker() -> None:
    """Ticker should always be uppercased regardless of input."""
    row = OHLCVRow(
        time=datetime.now(UTC),
        ticker="  msft  ",
        interval="1d",
        open=Decimal("300.00"),
        high=Decimal("305.00"),
        low=Decimal("298.00"),
        close=Decimal("302.00"),
        volume=20_000_000,
    )
    assert row.ticker == "MSFT"


@pytest.mark.unit
def test_ohlcv_row_rejects_negative_price() -> None:
    """Negative prices should raise a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        OHLCVRow(
            time=datetime.now(UTC),
            ticker="AAPL",
            interval="1d",
            open=Decimal("-1.00"),  # invalid
            high=Decimal("155.00"),
            low=Decimal("149.00"),
            close=Decimal("153.00"),
            volume=50_000_000,
        )
    assert "positive" in str(exc_info.value).lower()


@pytest.mark.unit
def test_ohlcv_row_rejects_zero_price() -> None:
    """Zero prices should also be rejected."""
    with pytest.raises(ValidationError):
        OHLCVRow(
            time=datetime.now(UTC),
            ticker="AAPL",
            interval="1d",
            open=Decimal("0"),  # invalid
            high=Decimal("155.00"),
            low=Decimal("149.00"),
            close=Decimal("153.00"),
            volume=50_000_000,
        )


@pytest.mark.unit
def test_ohlcv_row_rejects_negative_volume() -> None:
    """Negative volume should raise a ValidationError."""
    with pytest.raises(ValidationError):
        OHLCVRow(
            time=datetime.now(UTC),
            ticker="AAPL",
            interval="1d",
            open=Decimal("150.00"),
            high=Decimal("155.00"),
            low=Decimal("149.00"),
            close=Decimal("153.00"),
            volume=-1,  # invalid
        )


@pytest.mark.unit
def test_ohlcv_row_allows_zero_volume() -> None:
    """Zero volume is valid (e.g. halted stocks, weekends in crypto)."""
    row = OHLCVRow(
        time=datetime.now(UTC),
        ticker="AAPL",
        interval="1d",
        open=Decimal("150.00"),
        high=Decimal("155.00"),
        low=Decimal("149.00"),
        close=Decimal("153.00"),
        volume=0,
    )
    assert row.volume == 0


@pytest.mark.unit
def test_company_info_row_valid() -> None:
    """A valid CompanyInfoRow should parse correctly."""
    row = CompanyInfoRow(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        description="Apple makes iPhones.",
        market_cap=3_000_000_000_000,
        updated_at=datetime.now(UTC),
    )
    assert row.ticker == "AAPL"
    assert row.market_cap == 3_000_000_000_000


@pytest.mark.unit
def test_company_info_row_optional_fields() -> None:
    """CompanyInfoRow should work with only required fields."""
    row = CompanyInfoRow(
        ticker="AAPL",
        name="Apple Inc.",
        updated_at=datetime.now(UTC),
    )
    assert row.sector is None
    assert row.industry is None
    assert row.description is None
    assert row.market_cap is None


# ── ensure_min_bars / ensure_company_info: auto-ingest control flow ──


class _FakeCountResult:
    """Minimal stand-in for the SQLAlchemy Result returned by db.execute()."""

    def __init__(self, count: int) -> None:
        self._count = count

    def scalar_one(self) -> int:
        return self._count


class _FakeDB:
    """Minimal AsyncSession stand-in - only the two methods these
    functions actually call."""

    def __init__(self, count: int = 0, company: object | None = None) -> None:
        self._count = count
        self._company = company

    async def execute(self, *_args: object, **_kwargs: object) -> _FakeCountResult:
        return _FakeCountResult(self._count)

    async def get(self, *_args: object, **_kwargs: object) -> object | None:
        return self._company


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_min_bars_skips_when_already_sufficient() -> None:
    db = _FakeDB(count=200)
    with patch(
        "app.data.ingestion.market_data.fetch_and_store_ohlcv", AsyncMock()
    ) as mock_fetch:
        await ensure_min_bars(db, "AAPL", min_rows=60)  # type: ignore[arg-type]
        mock_fetch.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_min_bars_ingests_when_insufficient() -> None:
    db = _FakeDB(count=10)
    with patch(
        "app.data.ingestion.market_data.fetch_and_store_ohlcv", AsyncMock()
    ) as mock_fetch:
        await ensure_min_bars(db, "aapl", min_rows=60)  # type: ignore[arg-type]
        mock_fetch.assert_called_once()
        args, _ = mock_fetch.call_args
        assert args[1] == "AAPL"  # normalised to uppercase


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_min_bars_swallows_fetch_failure() -> None:
    db = _FakeDB(count=0)
    with patch(
        "app.data.ingestion.market_data.fetch_and_store_ohlcv",
        AsyncMock(side_effect=ValueError("no data for ticker")),
    ):
        await ensure_min_bars(db, "ZZZZZ", min_rows=60)  # type: ignore[arg-type]  # must not raise


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_company_info_skips_when_present() -> None:
    db = _FakeDB(company=object())
    with patch(
        "app.data.ingestion.market_data.fetch_and_store_company_info", AsyncMock()
    ) as mock_fetch:
        await ensure_company_info(db, "AAPL")  # type: ignore[arg-type]
        mock_fetch.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_company_info_fetches_when_missing() -> None:
    db = _FakeDB(company=None)
    with patch(
        "app.data.ingestion.market_data.fetch_and_store_company_info", AsyncMock()
    ) as mock_fetch:
        await ensure_company_info(db, "aapl")  # type: ignore[arg-type]
        mock_fetch.assert_called_once()
        args, _ = mock_fetch.call_args
        assert args[1] == "AAPL"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_company_info_swallows_fetch_failure() -> None:
    db = _FakeDB(company=None)
    with patch(
        "app.data.ingestion.market_data.fetch_and_store_company_info",
        AsyncMock(side_effect=ValueError("no info for ticker")),
    ):
        await ensure_company_info(db, "ZZZZZ")  # type: ignore[arg-type]  # must not raise
