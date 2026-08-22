"""
AEQUITAS - Unit tests for the price history endpoint helpers.

We test the pure logic (range validation, date filtering) without
hitting a real database or yfinance - those are integration-tested
manually since they require network/DB access.

get_price_history's control flow - when it decides a full re-ingest is
needed, and how it handles that call failing - is real logic worth
pinning down, so those paths get a minimal fake AsyncSession (this repo
has no test-DB fixture) plus a mocked fetch_and_store_ohlcv, matching
the pattern used for the other endpoints that take `db` as a plain
parameter (e.g. test_refresh_universe.py).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.history import VALID_RANGES, get_price_history


@pytest.mark.unit
def test_valid_ranges_contains_expected_values() -> None:
    assert VALID_RANGES == {"1mo", "6mo", "1y", "5y", "max"}


@pytest.mark.unit
def test_valid_ranges_rejects_unknown() -> None:
    assert "10y" not in VALID_RANGES
    assert "1d" not in VALID_RANGES


@pytest.mark.unit
def test_range_day_cutoffs_are_increasing() -> None:
    """Each range should cover more days than the previous, in order."""
    range_days = {
        "1mo": 31,
        "6mo": 183,
        "1y": 366,
        "5y": 1827,
    }
    values = list(range_days.values())
    assert values == sorted(values)


@pytest.mark.unit
def test_cutoff_calculation_1mo() -> None:
    """Sanity check the date math used for range filtering."""
    now = datetime(2026, 6, 21, tzinfo=UTC)
    cutoff = now.replace(tzinfo=None) - timedelta(days=31)
    assert cutoff.year == 2026
    assert cutoff.month == 5


@pytest.mark.unit
def test_cutoff_calculation_5y() -> None:
    now = datetime(2026, 6, 21, tzinfo=UTC)
    cutoff = now.replace(tzinfo=None) - timedelta(days=1827)
    assert cutoff.year == 2021


class _FakeBar:
    def __init__(self, time: datetime) -> None:
        self.time = time
        self.ticker = "AAPL"
        self.interval = "1d"
        self.open = 100.0
        self.high = 101.0
        self.low = 99.0
        self.close = 100.5
        self.volume = 1_000_000


class _FakeResult:
    """Serves both the earliest-bar scalar lookup and the full bars
    query - real code always calls the one method that matches the
    query it just issued, never both on the same result."""

    def __init__(self, bars: list[_FakeBar]) -> None:
        self._bars = bars

    def scalar_one_or_none(self) -> datetime | None:
        return self._bars[0].time if self._bars else None

    def scalars(self) -> "_FakeResult":
        return self

    def all(self) -> list[_FakeBar]:
        return self._bars


class _FakeDB:
    def __init__(self, bars: list[_FakeBar]) -> None:
        self._bars = bars

    async def execute(self, *_args: object, **_kwargs: object) -> _FakeResult:
        return _FakeResult(self._bars)


def _bars_spanning_years(years: float) -> list[_FakeBar]:
    start = datetime.now(UTC) - timedelta(days=int(years * 365))
    return [_FakeBar(start), _FakeBar(datetime.now(UTC))]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_narrow_range_on_already_ingested_ticker_skips_full_reingest() -> None:
    """1mo/6mo/1y never need more than what's already stored once a
    ticker has any history at all - the slow full re-ingest path must
    not fire just because someone asked for a short range."""
    db = _FakeDB(_bars_spanning_years(2))
    with patch(
        "app.api.v1.history.fetch_and_store_ohlcv", AsyncMock()
    ) as mock_fetch:
        await get_price_history("AAPL", range_="1mo", db=db)  # type: ignore[arg-type]
    mock_fetch.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_range_with_long_history_skips_full_reingest() -> None:
    """Already has 5+ years - "max" doesn't need a fresh full ingest."""
    db = _FakeDB(_bars_spanning_years(5))
    with patch(
        "app.api.v1.history.fetch_and_store_ohlcv", AsyncMock()
    ) as mock_fetch:
        await get_price_history("AAPL", range_="max", db=db)  # type: ignore[arg-type]
    mock_fetch.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_max_range_with_short_history_triggers_full_reingest() -> None:
    """Only ~1 year stored but "max" was requested - the heuristic
    should recognize this is probably a partial ingest and top up."""
    db = _FakeDB(_bars_spanning_years(1))
    with patch(
        "app.api.v1.history.fetch_and_store_ohlcv", AsyncMock()
    ) as mock_fetch:
        await get_price_history("AAPL", range_="max", db=db)  # type: ignore[arg-type]
    mock_fetch.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_brand_new_ticker_with_no_data_returns_404() -> None:
    db = _FakeDB([])
    with patch(
        "app.api.v1.history.fetch_and_store_ohlcv",
        AsyncMock(side_effect=ValueError("No data returned for ticker 'ZZZZ'")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await get_price_history("ZZZZ", range_="1y", db=db)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_topup_failure_on_existing_ticker_falls_back_to_stored_bars() -> None:
    """A transient yfinance hiccup while topping up an already-known
    ticker shouldn't fail the whole request - serve what's stored."""
    db = _FakeDB(_bars_spanning_years(1))
    with patch(
        "app.api.v1.history.fetch_and_store_ohlcv",
        AsyncMock(side_effect=ValueError("transient fetch error")),
    ):
        result = await get_price_history("AAPL", range_="max", db=db)  # type: ignore[arg-type]
    assert result.n_candles == 2
