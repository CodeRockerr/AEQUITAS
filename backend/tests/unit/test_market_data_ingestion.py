"""
AEQUITAS — Unit tests for market data validation layer.

These tests cover the Pydantic validation models only.
No database, no yFinance calls — pure logic tests.
Fast to run, easy to understand.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.data.ingestion.market_data import CompanyInfoRow, OHLCVRow


@pytest.mark.unit
def test_ohlcv_row_valid() -> None:
    """A well-formed OHLCV row should validate successfully."""
    row = OHLCVRow(
        time=datetime.now(UTC),
        ticker="aapl",  # lowercase — should be normalised
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
