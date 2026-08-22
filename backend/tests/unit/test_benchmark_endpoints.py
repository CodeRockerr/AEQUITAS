"""
AEQUITAS - Smoke tests for the extended benchmark endpoints: NumPy
middle-ground comparison, thread-count scaling sweep, and the NaN
edge-case explorer.
"""

import io
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from app.algorithms.ml.features_cpp import CPP_AVAILABLE
from app.api.v1.benchmark import (
    MAX_PIPELINE_ROWS,
    REAL_BACKTEST_TICKERS,
    SCALING_SYMBOLS,
    _effective_cpu_count,
    _macd_entries_exits,
    _synthetic_ohlcv_df,
    benchmark_edge_case,
    benchmark_kernels,
    benchmark_parallel,
    benchmark_pipeline,
    benchmark_scaling,
)


def _fake_open(responses: dict[str, str]):
    """Stand-in for builtins.open: paths in `responses` yield a file-like
    object over that text, everything else raises OSError (as a missing
    cgroup file/interface would on a non-Linux or unconfined host)."""

    def opener(path, *args, **kwargs):
        if path in responses:
            return io.StringIO(responses[path])
        raise OSError(f"no such file: {path}")

    return opener


@pytest.mark.unit
def test_effective_cpu_count_reads_cgroup_v2_quota() -> None:
    opener = _fake_open({"/sys/fs/cgroup/cpu.max": "200000 100000\n"})
    with patch("builtins.open", opener):
        assert _effective_cpu_count() == 2


@pytest.mark.unit
def test_effective_cpu_count_falls_back_from_unlimited_v2_to_v1() -> None:
    opener = _fake_open(
        {
            "/sys/fs/cgroup/cpu.max": "max 100000\n",
            "/sys/fs/cgroup/cpu/cpu.cfs_quota_us": "150000\n",
            "/sys/fs/cgroup/cpu/cpu.cfs_period_us": "100000\n",
        }
    )
    with patch("builtins.open", opener):
        # 150000/100000 = 1.5 cores - rounds down, never up, to avoid the
        # oversubscription this function exists to prevent.
        assert _effective_cpu_count() == 1


@pytest.mark.unit
def test_effective_cpu_count_falls_back_to_os_cpu_count_on_unlimited_v1() -> None:
    # v1 quota=-1 is cgroup's "no limit set" - must fall through to
    # os.cpu_count() rather than treating -1 itself as a core count.
    opener = _fake_open({"/sys/fs/cgroup/cpu/cpu.cfs_quota_us": "-1\n"})
    with patch("builtins.open", opener), patch("os.cpu_count", return_value=8):
        assert _effective_cpu_count() == 8


@pytest.mark.unit
def test_effective_cpu_count_falls_back_to_os_cpu_count_when_unconfined() -> None:
    # No cgroup interface at all, e.g. a macOS/Windows dev machine.
    opener = _fake_open({})
    with patch("builtins.open", opener), patch("os.cpu_count", return_value=8):
        assert _effective_cpu_count() == 8


@pytest.mark.unit
def test_synthetic_ohlcv_price_stays_bounded_at_max_pipeline_rows() -> None:
    # A driftful (or even driftless) random walk's cumulative sum grows
    # with rows - the old generator put "close" at ~1e27 by
    # MAX_PIPELINE_ROWS, far past where float64 has any real precision.
    # The mean-reverting walk should stay in a realistic band regardless
    # of row count.
    df = _synthetic_ohlcv_df(MAX_PIPELINE_ROWS)
    close = df["close"]
    assert close.min() > 0.5
    assert close.max() < 5_000


pytestmark = pytest.mark.skipif(
    not CPP_AVAILABLE, reason="aequitas_kernels extension not built"
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kernels_includes_numpy_and_memory_fields() -> None:
    r = await benchmark_kernels(rows=5_000, ticker=None, db=None)  # type: ignore[arg-type]
    for result in r.results:
        assert result.numpy_ms is not None
        assert result.numpy_max_abs_diff is not None
        assert result.pandas_peak_kb > 0
        assert result.cpp_peak_kb is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scaling_sweep_returns_all_thread_counts() -> None:
    r = await benchmark_scaling(rows=10_000, real_data=False, db=None)  # type: ignore[arg-type]
    assert [p.threads for p in r.points] == [1, 2, 4, 8]
    assert all(p.ms > 0 for p in r.points)


@pytest.mark.unit
@pytest.mark.parametrize(
    "scenario", ["clean", "leading_nan", "interior_nan", "all_nan"]
)
def test_edge_case_rolling_std_always_matches_pandas(scenario: str) -> None:
    # rolling_std was fixed to be NaN-safe on every scenario.
    r = benchmark_edge_case(scenario=scenario, kernel="rolling_std")
    assert r.cpp_matches_pandas is True
    assert r.numpy_matches_pandas is True


@pytest.mark.unit
def test_edge_case_rolling_max_known_limitation() -> None:
    # rolling_max/min are documented as NaN-unsafe - this pins down that
    # honestly-disclosed limitation as a regression check, not a silent bug.
    clean = benchmark_edge_case(scenario="clean", kernel="rolling_max")
    assert clean.cpp_matches_pandas is True

    with_nan = benchmark_edge_case(scenario="interior_nan", kernel="rolling_max")
    assert with_nan.cpp_matches_pandas is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_benchmark_agrees_with_pandas_at_max_rows() -> None:
    # Regression: at MAX_PIPELINE_ROWS this used to either crash (a date
    # overflow in the old synthetic-data generator) or silently report a
    # huge max_abs_diff (the old generator's price wandering far enough
    # that pandas/C++ EMA-based features diverged in float64 precision,
    # not a real kernel bug). Both are fixed at the data-generation layer.
    # db is unused on the synthetic (no-ticker) path. ticker must be passed
    # explicitly here: calling a FastAPI endpoint directly (bypassing
    # routing) means an omitted Query(...) parameter keeps the raw Query
    # sentinel object as its default, not the None that default= implies -
    # `if ticker:` would then be true for that (truthy) sentinel object.
    r = await benchmark_pipeline(rows=MAX_PIPELINE_ROWS, ticker=None, db=None)  # type: ignore[arg-type]
    assert r.cpp_available is True
    assert r.max_abs_diff is not None
    assert r.max_abs_diff < 1e-6


class _FakeOhlcvRow:
    def __init__(self, time: datetime, price: float) -> None:
        self.time = time
        self.open = price
        self.high = price * 1.01
        self.low = price * 0.99
        self.close = price
        self.volume = 1_000_000


class _FakeOhlcvResult:
    def __init__(self, rows: list[_FakeOhlcvRow]) -> None:
        self._rows = rows

    def all(self) -> list[_FakeOhlcvRow]:
        return self._rows


class _FakeOhlcvDB:
    def __init__(self, rows: list[_FakeOhlcvRow]) -> None:
        self._rows = rows

    async def execute(self, *_args: object, **_kwargs: object) -> _FakeOhlcvResult:
        return _FakeOhlcvResult(self._rows)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_benchmark_with_ticker_uses_real_data() -> None:
    """Passing `ticker` should route through _fetch_real_ohlcv instead of
    the synthetic generator, and the response should say so."""
    # Sine-wave oscillation, not a monotonic price - a strictly-increasing
    # series has zero down-days ever, which is a real edge case in _rsi()
    # (avg_loss stays exactly 0, and RSI ends up NaN for the whole
    # series instead of the mathematically correct 100). Matches the
    # synthetic-price pattern already established in
    # test_close_series_helpers.py for the same reason.
    db = _FakeOhlcvDB(_sine_wave_rows())

    r = await benchmark_pipeline(ticker="aapl", db=db)  # type: ignore[arg-type]

    assert r.ticker == "AAPL"
    assert r.start_date is not None
    assert r.end_date is not None
    assert "real AAPL history" in r.note


def _sine_wave_rows(n: int = 400) -> list[_FakeOhlcvRow]:
    import math

    base = datetime(2020, 1, 1)
    return [
        _FakeOhlcvRow(base + timedelta(days=i), 100.0 + 10 * math.sin(i / 8) + i * 0.05)
        for i in range(n)
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kernels_benchmark_with_ticker_uses_real_data() -> None:
    """Passing `ticker` should route /kernels through _fetch_real_ohlcv
    instead of the synthetic generator, same as /pipeline."""
    db = _FakeOhlcvDB(_sine_wave_rows())

    r = await benchmark_kernels(rows=100_000, ticker="aapl", db=db)  # type: ignore[arg-type]

    assert r.ticker == "AAPL"
    assert r.start_date is not None
    assert r.end_date is not None
    assert r.rows == 400
    assert "real AAPL history" in r.note


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parallel_benchmark_real_data_caps_symbols_at_ticker_count() -> None:
    """Only REAL_BACKTEST_TICKERS (3) are ingested - requesting more
    symbols than that in real-data mode should cap, not error or fake
    extra symbols out of nowhere."""
    db = _FakeOhlcvDB(_sine_wave_rows())

    r = await benchmark_parallel(symbols=8, real_data=True, db=db)  # type: ignore[arg-type]

    assert r.tickers == REAL_BACKTEST_TICKERS
    assert r.symbols == len(REAL_BACKTEST_TICKERS)
    assert "real data" in r.note


@pytest.mark.unit
@pytest.mark.asyncio
async def test_scaling_benchmark_real_data_cycles_tickers_to_fill_slots() -> None:
    """The scaling sweep needs a fixed 8-symbol workload, but only 3 real
    tickers are ingested - real-data mode should cycle them to fill every
    thread-pool slot rather than fail or silently drop to 3 symbols."""
    db = _FakeOhlcvDB(_sine_wave_rows())

    r = await benchmark_scaling(real_data=True, db=db)  # type: ignore[arg-type]

    assert r.tickers is not None
    assert len(r.tickers) == SCALING_SYMBOLS
    assert r.tickers[: len(REAL_BACKTEST_TICKERS)] == REAL_BACKTEST_TICKERS
    assert r.tickers[len(REAL_BACKTEST_TICKERS)] == REAL_BACKTEST_TICKERS[0]


@pytest.mark.unit
def test_macd_entries_exits_matches_backtest_engine_rule() -> None:
    # Same crossover rule as run_macd_backtest() in the backtesting engine,
    # just fed by an already-computed macd_hist column instead of
    # recomputing MACD inline - this pins down that they stay in sync.
    hist = pd.Series([-1.0, -0.5, 0.5, 1.0, 0.5, -0.5, -1.0])
    feat = pd.DataFrame({"macd_hist": hist})

    entries, exits = _macd_entries_exits(feat)

    assert entries.tolist() == [False, False, True, False, False, False, False]
    assert exits.tolist() == [False, False, False, False, False, True, False]
