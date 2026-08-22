"""
AEQUITAS - Unit tests for the bulk ticker-universe refresh endpoint.

refresh_universe takes `db` as a plain parameter and calls
fetch_and_store_ohlcv per ticker, so a minimal fake session (this repo
has no test-DB fixture) plus a mocked fetch function exercises the
real per-ticker commit/rollback isolation - the actual point of this
endpoint: one bad ticker (delisted symbol, transient yFinance hiccup)
must not abort the rest of the batch.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.market_data import refresh_universe
from app.data.ingestion.universe import TICKER_UNIVERSE


class _FakeDB:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_universe_covers_every_ticker_in_the_universe() -> None:
    db = _FakeDB()
    with patch(
        "app.api.v1.market_data.fetch_and_store_ohlcv",
        AsyncMock(return_value=10),
    ):
        result = await refresh_universe(period="5d", interval="1d", db=db)  # type: ignore[arg-type]

    assert {r.ticker for r in result.results} == set(TICKER_UNIVERSE)
    assert result.succeeded == len(TICKER_UNIVERSE)
    assert result.failed == 0
    assert db.commits == len(TICKER_UNIVERSE)
    assert db.rollbacks == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_universe_isolates_a_single_ticker_failure() -> None:
    """One delisted/failing ticker must not abort the rest of the batch,
    and must roll back only its own (non-existent) writes."""
    db = _FakeDB()

    async def fake_fetch(_db: object, ticker: str, _period: str, _interval: str) -> int:
        if ticker == "BRK-B":
            raise ValueError("No data returned for ticker 'BRK-B'")
        return 5

    with patch("app.api.v1.market_data.fetch_and_store_ohlcv", fake_fetch):
        result = await refresh_universe(period="5d", interval="1d", db=db)  # type: ignore[arg-type]

    assert result.succeeded == len(TICKER_UNIVERSE) - 1
    assert result.failed == 1
    failed_result = next(r for r in result.results if r.ticker == "BRK-B")
    assert failed_result.error is not None
    assert "No data returned" in failed_result.error
    assert failed_result.rows_ingested is None

    other_results = [r for r in result.results if r.ticker != "BRK-B"]
    assert all(r.error is None and r.rows_ingested == 5 for r in other_results)
    assert db.rollbacks == 1
    assert db.commits == len(TICKER_UNIVERSE) - 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_universe_reports_period_and_interval_used() -> None:
    db = _FakeDB()
    with patch(
        "app.api.v1.market_data.fetch_and_store_ohlcv",
        AsyncMock(return_value=1),
    ):
        result = await refresh_universe(period="max", interval="1d", db=db)  # type: ignore[arg-type]

    assert result.period == "max"
    assert result.interval == "1d"
