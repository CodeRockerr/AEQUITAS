"""
AEQUITAS - Unit tests for _get_close_series (signals.py) and
_get_log_returns (advanced.py).

Both take `db` as a plain parameter, so a minimal fake AsyncSession
(this repo has no test-DB fixture) exercises their real row-count
validation and max_rows capping logic directly - including the actual
fix this session made for the return-compounding blowup (uncapped
history compounding into +23 trillion% totals), which had only been
verified manually against the real DB before now.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.advanced import _get_log_returns
from app.api.v1.signals import _get_close_series, run_backtest


class _FakeRow:
    def __init__(self, time: datetime, close: float) -> None:
        self.time = time
        self.close = close


class _FakeRowsResult:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    def all(self) -> list[_FakeRow]:
        return self._rows


class _FakeDB:
    def __init__(self, rows: list[_FakeRow]) -> None:
        self._rows = rows

    async def execute(self, *_args: object, **_kwargs: object) -> _FakeRowsResult:
        return _FakeRowsResult(self._rows)


def _make_rows(n: int, start_price: float = 100.0) -> list[_FakeRow]:
    base = datetime(2020, 1, 1)
    return [_FakeRow(base + timedelta(days=i), start_price + i) for i in range(n)]


# ── _get_close_series (signals.py) ────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_close_series_auto_ingests_via_ensure_min_bars() -> None:
    db = _FakeDB(_make_rows(100))
    with patch("app.api.v1.signals.ensure_min_bars", AsyncMock()) as mock_ensure:
        series = await _get_close_series(db, "aapl", min_rows=60)  # type: ignore[arg-type]
    mock_ensure.assert_called_once()
    assert len(series) == 100
    assert series.name == "AAPL"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_close_series_raises_404_when_still_insufficient() -> None:
    """Even after the (mocked) auto-ingest attempt, too few rows is a 404,
    not a silent empty series."""
    db = _FakeDB(_make_rows(10))
    with patch("app.api.v1.signals.ensure_min_bars", AsyncMock()):
        with pytest.raises(HTTPException) as exc_info:
            await _get_close_series(db, "AAPL", min_rows=60)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_close_series_caps_to_max_rows() -> None:
    """The actual fix for the return-compounding blowup: a backtest over
    AAPL's full 45-year history compounded into +23 trillion% totals
    until max_rows capped it to a recent window."""
    db = _FakeDB(_make_rows(2000))
    with patch("app.api.v1.signals.ensure_min_bars", AsyncMock()):
        series = await _get_close_series(db, "AAPL", min_rows=60, max_rows=1260)  # type: ignore[arg-type]
    assert len(series) == 1260
    # capping should keep the MOST RECENT rows, not the earliest
    assert series.iloc[-1] == 100.0 + 1999


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_close_series_uncapped_when_max_rows_none() -> None:
    db = _FakeDB(_make_rows(500))
    with patch("app.api.v1.signals.ensure_min_bars", AsyncMock()):
        series = await _get_close_series(db, "AAPL", min_rows=60, max_rows=None)  # type: ignore[arg-type]
    assert len(series) == 500


# ── _get_log_returns (advanced.py) ─────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_log_returns_auto_ingests_via_ensure_min_bars() -> None:
    db = _FakeDB(_make_rows(100))
    with patch("app.api.v1.advanced.ensure_min_bars", AsyncMock()) as mock_ensure:
        returns = await _get_log_returns(db, "tsla", min_rows=60)  # type: ignore[arg-type]
    mock_ensure.assert_called_once()
    # one row consumed by the pct_change/dropna at the start of the series
    assert len(returns) == 99


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_log_returns_raises_404_when_still_insufficient() -> None:
    db = _FakeDB(_make_rows(10))
    with patch("app.api.v1.advanced.ensure_min_bars", AsyncMock()):
        with pytest.raises(HTTPException) as exc_info:
            await _get_log_returns(db, "TSLA", min_rows=60)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 404


# ── run_backtest (signals.py) ──────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_backtest_rejects_unknown_strategy() -> None:
    """Validation happens before `db` is ever touched, so this needs
    no fake session at all."""
    with pytest.raises(HTTPException) as exc_info:
        await run_backtest(ticker="AAPL", strategy="not-a-real-strategy", db=None)  # type: ignore[arg-type]
    assert exc_info.value.status_code == 422


def _make_oscillating_rows(n: int) -> list[_FakeRow]:
    """A synthetic price series with enough variation for RSI/MACD/
    Bollinger to compute real (non-degenerate) signals - a flat series
    would divide by zero in a few of these indicators."""
    import math

    base = datetime(2020, 1, 1)
    return [
        _FakeRow(base + timedelta(days=i), 100.0 + 10 * math.sin(i / 8) + i * 0.05)
        for i in range(n)
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_backtest_returns_real_equity_curve() -> None:
    """
    End-to-end regression test for this session's two backtest fixes:
    the max_rows cap (prevents the return-compounding blowup) and
    returning the real per-day equity curve (previously computed and
    discarded, forcing the frontend to fake one with Math.random()).
    """
    db = _FakeDB(_make_oscillating_rows(300))
    with patch("app.api.v1.signals.ensure_min_bars", AsyncMock()):
        result = await run_backtest(ticker="AAPL", strategy="rsi", db=db)  # type: ignore[arg-type]

    assert result.ticker == "AAPL"
    assert result.n_bars <= 300
    assert len(result.equity_curve) == result.n_bars
    assert len(result.benchmark_equity_curve) == result.n_bars
    assert result.equity_curve[0] == pytest.approx(10_000.0, rel=0.01)
    assert result.benchmark_equity_curve[0] == pytest.approx(10_000.0, rel=0.01)
