"""
AEQUITAS - Live Python vs C++ kernel benchmark.

GET /api/v1/benchmark/kernels?rows=100000    per-kernel timings
GET /api/v1/benchmark/pipeline?rows=50000    full 19-feature compute_features
GET /api/v1/benchmark/parallel?rows=200000&symbols=4   multi-symbol GIL release

Runs the pandas implementations from features.py head-to-head against
the C++ kernels (backend/cpp, pybind11) on identical synthetic OHLCV
data, and returns median wall-clock timings plus numerical agreement.

Degrades gracefully: if the extension isn't built in this deployment,
`cpp_available` is false and only pandas timings are returned.

Rows are capped to keep the endpoint cheap enough for the free-tier
Render deployment.
"""

import os
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from scipy.signal import lfilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.ml.features import ML_FEATURE_COLS, _atr, _rsi, compute_features
from app.algorithms.ml.features_cpp import CPP_AVAILABLE, compute_features_cpp
from app.algorithms.ml.features_numpy import (
    atr_numpy,
    ewm_mean_numpy,
    rolling_max_numpy,
    rolling_std_numpy,
    rsi_numpy,
)
from app.backtesting.engine import _simulate_strategy
from app.db import get_db
from app.models.market_data import OHLCVBar
from app.redis_client import get_run_count, increment_run_count


def _effective_cpu_count() -> int:
    """os.cpu_count() reports the host machine's total cores, not a
    container's actual CPU quota - on a quota-limited deployment (e.g. a
    free-tier Render instance sharing an 8-core host but entitled to only
    a fraction of one), that mismatch makes a ThreadPoolExecutor sized
    off os.cpu_count() oversubscribe far past what's actually schedulable,
    turning "parallel" into contention overhead that's slower than
    sequential. Reads the cgroup CPU quota (v2, falling back to v1) where
    available, and falls back to os.cpu_count() everywhere else (e.g.
    local dev, non-Linux hosts, or an unlimited quota)."""
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            quota_str, period_str = f.read().split()
        if quota_str != "max":
            return max(1, int(quota_str) // int(period_str))
    except (OSError, ValueError):
        pass

    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as f:
            quota = int(f.read().strip())
        if quota > 0:
            with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as f:
                period = int(f.read().strip())
            return max(1, quota // period)
    except (OSError, ValueError):
        pass

    return os.cpu_count() or 1


try:
    import aequitas_kernels as ck
except ImportError:  # extension not built in this environment
    ck = None

router = APIRouter(prefix="/api/v1/benchmark")

MAX_ROWS = 500_000
REPS = 5

MAX_PIPELINE_ROWS = 200_000
PIPELINE_REPS = 3

MAX_PARALLEL_ROWS = 1_000_000
MAX_PARALLEL_SYMBOLS = 8
PARALLEL_REPS = 3


def _synthetic_ohlcv_df(rows: int, seed: int = 42) -> pd.DataFrame:
    """Synthetic OHLCV DataFrame for the pipeline benchmark - a
    mean-reverting log-price walk, same shape as the real market data
    compute_features expects (open/high/low/close/volume, DatetimeIndex)."""
    rng = np.random.default_rng(seed)
    # A plain (even driftless) random walk's cumulative sum grows with
    # sqrt(rows) in EITHER direction - unbounded, so it can still wander
    # arbitrarily far from a realistic price at large row counts (the old
    # +0.0003/step drift put "price" at ~1e27 by MAX_PIPELINE_ROWS, and a
    # driftless walk still occasionally neared zero at the same size).
    # Both surfaced as pandas/C++ EMA-based features (macd, atr, bb_*)
    # spuriously diverging or dividing by ~0 - a synthetic-data artifact,
    # not a real kernel discrepancy. A mean-reverting log-price (AR(1) via
    # scipy.signal.lfilter, the same vectorized-recurrence trick used in
    # features_numpy.py) keeps "close" in a realistic band around $100
    # regardless of how many rows are requested.
    kappa = 0.001  # reversion speed; stationary std of log-price ~= 0.015/sqrt(2*kappa)
    target_log_price = np.log(100)
    noise = rng.normal(0, 0.015, rows)
    log_price = lfilter([1.0], [1.0, -(1 - kappa)], kappa * target_log_price + noise)
    close = np.exp(log_price)
    high = close * (1 + rng.uniform(0, 0.02, rows))
    low = close * (1 - rng.uniform(0, 0.02, rows))
    open_ = close * (1 + rng.normal(0, 0.005, rows))
    volume = rng.integers(1_000_000, 10_000_000, rows).astype(float)
    # unit="s": at the largest supported row counts, "B"-frequency dates
    # anchored at 2010 run out past the year 2262 - nanosecond-resolution
    # timestamps (pandas' default) overflow there, but second resolution
    # doesn't, and nothing here needs sub-second precision anyway.
    idx = pd.date_range("2010-01-01", periods=rows, freq="B", unit="s")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


class KernelResult(BaseModel):
    kernel: str
    description: str
    pandas_ms: float
    pandas_cold_ms: float  # first-call timing, before any allocator/CPU warm-up
    pandas_peak_kb: float
    cpp_ms: float | None
    cpp_cold_ms: float | None
    cpp_peak_kb: float | None
    speedup: float | None
    max_abs_diff: float | None  # numerical agreement, None if C++ missing
    numpy_ms: float | None
    numpy_peak_kb: float | None
    numpy_speedup: float | None
    numpy_max_abs_diff: float | None  # NumPy vs pandas


class BenchmarkResponse(BaseModel):
    rows: int
    reps: int
    cpp_available: bool
    note: str
    results: list[KernelResult]


def _median_ms(fn, reps: int = REPS) -> tuple[float, float, np.ndarray]:
    """Median + first-call ("cold") wall-clock ms over `reps` runs.

    Returns (median_ms, cold_ms, last_result). tracemalloc is deliberately
    NOT active during these reps - it has real overhead and would bias the
    very numbers this function exists to measure honestly.
    """
    out = None
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    return float(np.median(ts)), ts[0], np.asarray(out, dtype=float)


def _peak_kb(fn) -> float:
    """Peak traced-memory delta (KB) for one isolated call to `fn`.

    Measured in its own pass, never mixed with the timed reps above -
    tracemalloc's bookkeeping overhead would otherwise slow down (and
    skew) the wall-clock numbers.
    """
    tracemalloc.start()
    baseline, _ = tracemalloc.get_traced_memory()
    fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return (peak - baseline) / 1024


@router.get("/kernels", response_model=BenchmarkResponse)
def benchmark_kernels(
    rows: int = Query(default=100_000, ge=1_000, le=MAX_ROWS),
) -> BenchmarkResponse:
    increment_run_count()
    # Deterministic synthetic OHLCV - geometric random walk
    rng = np.random.default_rng(42)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, rows)))
    high = close * (1 + np.abs(rng.normal(0, 0.005, rows)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, rows)))
    s = pd.Series(close)
    hs, ls = pd.Series(high), pd.Series(low)

    cases = [
        (
            "rolling_std_21",
            "21-day realized volatility (rolling std)",
            lambda: s.rolling(21).std(),
            lambda: rolling_std_numpy(close, 21),
            (lambda: ck.rolling_std(close, 21)) if ck else None,
        ),
        (
            "rolling_max_252",
            "52-week high (rolling max, min_periods=1)",
            lambda: hs.rolling(252, min_periods=1).max(),
            lambda: rolling_max_numpy(high, 252, 1),
            (lambda: ck.rolling_max(high, 252, 1)) if ck else None,
        ),
        (
            "ewm_span_12",
            "12-day EMA (MACD building block)",
            lambda: s.ewm(span=12, adjust=False).mean(),
            lambda: ewm_mean_numpy(close, 2 / 13, 0),
            (lambda: ck.ewm_mean(close, 2 / 13, 0)) if ck else None,
        ),
        (
            "rsi_14",
            "RSI-14, Wilder smoothing",
            lambda: _rsi(s, 14),
            lambda: rsi_numpy(close, 14),
            (lambda: ck.rsi(close, 14)) if ck else None,
        ),
        (
            "atr_14",
            "Average True Range 14",
            lambda: _atr(hs, ls, s, 14),
            lambda: atr_numpy(high, low, close, 14),
            (lambda: ck.atr(high, low, close, 14)) if ck else None,
        ),
    ]

    results: list[KernelResult] = []
    for name, desc, pfn, nfn, cfn in cases:
        p_ms, p_cold_ms, p_out = _median_ms(pfn)
        p_peak_kb = _peak_kb(pfn)

        n_ms, _, n_out = _median_ms(nfn)
        n_peak_kb = _peak_kb(nfn)
        n_diff = float(np.nanmax(np.abs(p_out - n_out)))

        if cfn is not None:
            c_ms, c_cold_ms, c_out = _median_ms(cfn)
            c_peak_kb = _peak_kb(cfn)
            diff = float(np.nanmax(np.abs(p_out - c_out)))
            results.append(
                KernelResult(
                    kernel=name,
                    description=desc,
                    pandas_ms=round(p_ms, 3),
                    pandas_cold_ms=round(p_cold_ms, 3),
                    pandas_peak_kb=round(p_peak_kb, 1),
                    cpp_ms=round(c_ms, 3),
                    cpp_cold_ms=round(c_cold_ms, 3),
                    cpp_peak_kb=round(c_peak_kb, 1),
                    speedup=round(p_ms / c_ms, 1) if c_ms > 0 else None,
                    max_abs_diff=diff,
                    numpy_ms=round(n_ms, 3),
                    numpy_peak_kb=round(n_peak_kb, 1),
                    numpy_speedup=round(p_ms / n_ms, 1) if n_ms > 0 else None,
                    numpy_max_abs_diff=n_diff,
                )
            )
        else:
            results.append(
                KernelResult(
                    kernel=name,
                    description=desc,
                    pandas_ms=round(p_ms, 3),
                    pandas_cold_ms=round(p_cold_ms, 3),
                    pandas_peak_kb=round(p_peak_kb, 1),
                    cpp_ms=None,
                    cpp_cold_ms=None,
                    cpp_peak_kb=None,
                    speedup=None,
                    max_abs_diff=None,
                    numpy_ms=round(n_ms, 3),
                    numpy_peak_kb=round(n_peak_kb, 1),
                    numpy_speedup=round(p_ms / n_ms, 1) if n_ms > 0 else None,
                    numpy_max_abs_diff=n_diff,
                )
            )

    return BenchmarkResponse(
        rows=rows,
        reps=REPS,
        cpp_available=CPP_AVAILABLE,
        note=(
            "Timings are median wall-clock over "
            f"{REPS} runs on the API host; identical synthetic OHLCV inputs. "
            "numpy_* is a hand-vectorized NumPy implementation (sliding_window_view "
            "+ scipy.signal.lfilter), the middle option between pandas and C++. "
            "peak_kb is the peak traced-memory delta for one isolated call "
            "(tracemalloc, measured separately from the timed reps so it doesn't "
            "skew them). cold_ms is the first-rep timing, before any allocator/CPU "
            "warm-up; ms is the median of the remaining reps. max_abs_diff is the "
            "largest absolute deviation from the pandas output (NaN positions must "
            "match)."
        ),
        results=results,
    )


class PipelineBenchmarkResponse(BaseModel):
    rows: int
    output_rows: int
    reps: int
    cpp_available: bool
    pandas_ms: float
    cpp_ms: float | None
    speedup: float | None
    max_abs_diff: float | None
    note: str


@router.get("/pipeline", response_model=PipelineBenchmarkResponse)
def benchmark_pipeline(
    rows: int = Query(default=50_000, ge=1_000, le=MAX_PIPELINE_ROWS),
) -> PipelineBenchmarkResponse:
    """End-to-end benchmark: the full 19-feature compute_features() pipeline,
    pandas vs. the C++20-kernel-backed drop-in (features_cpp.py)."""
    increment_run_count()
    df = _synthetic_ohlcv_df(rows)
    compare_cols = ML_FEATURE_COLS + ["target_1d"]

    def median_ms(fn, reps: int) -> tuple[float, pd.DataFrame]:
        ts = []
        out = None
        for _ in range(reps):
            t0 = time.perf_counter()
            out = fn()
            ts.append((time.perf_counter() - t0) * 1e3)
        assert out is not None
        return float(np.median(ts)), out

    p_ms, p_out = median_ms(lambda: compute_features(df), PIPELINE_REPS)

    if not CPP_AVAILABLE:
        return PipelineBenchmarkResponse(
            rows=rows,
            output_rows=len(p_out),
            reps=PIPELINE_REPS,
            cpp_available=False,
            pandas_ms=round(p_ms, 2),
            cpp_ms=None,
            speedup=None,
            max_abs_diff=None,
            note="C++ extension not built on this host; pandas-only timing shown.",
        )

    c_ms, c_out = median_ms(lambda: compute_features_cpp(df), PIPELINE_REPS)
    diff = float((p_out[compare_cols] - c_out[compare_cols]).abs().to_numpy().max())

    return PipelineBenchmarkResponse(
        rows=rows,
        output_rows=len(p_out),
        reps=PIPELINE_REPS,
        cpp_available=True,
        pandas_ms=round(p_ms, 2),
        cpp_ms=round(c_ms, 2),
        speedup=round(p_ms / c_ms, 1) if c_ms > 0 else None,
        max_abs_diff=diff,
        note=(
            "Full 19-feature compute_features() pipeline, pandas vs the "
            f"C++20-kernel-backed drop-in, median wall-clock over {PIPELINE_REPS} "
            "runs on identical synthetic OHLCV input."
        ),
    )


class ParallelBenchmarkResponse(BaseModel):
    rows: int
    symbols: int
    reps: int
    cpp_available: bool
    cpu_count: int
    pandas_sequential_ms: float
    cpp_sequential_ms: float | None
    cpp_parallel_ms: float | None
    sequential_speedup: float | None
    parallel_speedup: float | None
    note: str


@router.get("/parallel", response_model=ParallelBenchmarkResponse)
def benchmark_parallel(
    rows: int = Query(default=200_000, ge=10_000, le=MAX_PARALLEL_ROWS),
    symbols: int = Query(default=4, ge=1, le=MAX_PARALLEL_SYMBOLS),
) -> ParallelBenchmarkResponse:
    """Multi-symbol RSI-14: pandas sequential vs. C++ sequential vs. C++
    driven from a Python ThreadPoolExecutor with the GIL released around
    each kernel call - the poster's headline result. Parallel speedup is
    bounded by the API host's core count, which is why cpu_count is
    reported alongside it."""
    increment_run_count()
    rng = np.random.default_rng(seed=42)
    closes = [
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, rows))) for _ in range(symbols)
    ]
    series = [pd.Series(c) for c in closes]

    def bench(fn) -> float:
        ts = []
        for _ in range(PARALLEL_REPS):
            t0 = time.perf_counter()
            fn()
            ts.append((time.perf_counter() - t0) * 1e3)
        return float(np.median(ts))

    p_ms = bench(lambda: [_rsi(s, 14) for s in series])
    cpu_count = _effective_cpu_count()

    if not CPP_AVAILABLE:
        return ParallelBenchmarkResponse(
            rows=rows,
            symbols=symbols,
            reps=PARALLEL_REPS,
            cpp_available=False,
            cpu_count=cpu_count,
            pandas_sequential_ms=round(p_ms, 2),
            cpp_sequential_ms=None,
            cpp_parallel_ms=None,
            sequential_speedup=None,
            parallel_speedup=None,
            note="C++ extension not built on this host; pandas-only timing shown.",
        )

    c_seq_ms = bench(lambda: [ck.rsi(c, 14) for c in closes])
    # Oversubscribing threads past the host's real quota turns "parallel"
    # into pure contention overhead - cap at what's actually schedulable.
    with ThreadPoolExecutor(max_workers=min(symbols, cpu_count)) as ex:
        c_par_ms = bench(lambda: list(ex.map(lambda c: ck.rsi(c, 14), closes)))

    return ParallelBenchmarkResponse(
        rows=rows,
        symbols=symbols,
        reps=PARALLEL_REPS,
        cpp_available=True,
        cpu_count=cpu_count,
        pandas_sequential_ms=round(p_ms, 2),
        cpp_sequential_ms=round(c_seq_ms, 2),
        cpp_parallel_ms=round(c_par_ms, 2),
        sequential_speedup=round(p_ms / c_seq_ms, 1) if c_seq_ms > 0 else None,
        parallel_speedup=round(p_ms / c_par_ms, 1) if c_par_ms > 0 else None,
        note=(
            f"RSI-14 across {symbols} symbols x {rows:,} rows: pandas sequential vs "
            "C++ sequential vs C++ driven from a ThreadPoolExecutor (GIL released "
            "around each kernel call). Parallel speedup is capped by cpu_count on "
            "the API host - it will be far smaller on a 1-2 vCPU deployment than "
            "on an 8-core dev machine."
        ),
    )


MAX_SCALING_ROWS = 500_000
SCALING_REPS = 3
SCALING_SYMBOLS = 8
SCALING_THREAD_COUNTS = [1, 2, 4, 8]


class ScalingPoint(BaseModel):
    threads: int
    ms: float
    speedup_vs_1_thread: float | None


class ScalingBenchmarkResponse(BaseModel):
    rows: int
    symbols: int
    cpp_available: bool
    cpu_count: int
    points: list[ScalingPoint]
    note: str


@router.get("/scaling", response_model=ScalingBenchmarkResponse)
def benchmark_scaling(
    rows: int = Query(default=100_000, ge=10_000, le=MAX_SCALING_ROWS),
) -> ScalingBenchmarkResponse:
    """Strong-scaling sweep: a FIXED workload (8 independent RSI-14
    computations) driven from thread pools of size 1/2/4/8, to find where
    the GIL-release payoff saturates against the host's actual core count -
    adding threads stops helping once you run out of cores, and that's the
    interesting part, not a bug."""
    increment_run_count()
    cpu_count = _effective_cpu_count()

    if not CPP_AVAILABLE:
        return ScalingBenchmarkResponse(
            rows=rows,
            symbols=SCALING_SYMBOLS,
            cpp_available=False,
            cpu_count=cpu_count,
            points=[],
            note="C++ extension not built on this host; no scaling data to show.",
        )

    rng = np.random.default_rng(seed=7)
    closes = [
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, rows)))
        for _ in range(SCALING_SYMBOLS)
    ]

    def bench_threads(n_threads: int) -> float:
        ts = []
        for _ in range(SCALING_REPS):
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=n_threads) as ex:
                list(ex.map(lambda c: ck.rsi(c, 14), closes))
            ts.append((time.perf_counter() - t0) * 1e3)
        return float(np.median(ts))

    points: list[ScalingPoint] = []
    base_ms: float | None = None
    for t in SCALING_THREAD_COUNTS:
        ms = bench_threads(t)
        if base_ms is None:
            base_ms = ms
        points.append(
            ScalingPoint(
                threads=t,
                ms=round(ms, 2),
                speedup_vs_1_thread=round(base_ms / ms, 2) if ms > 0 else None,
            )
        )

    return ScalingBenchmarkResponse(
        rows=rows,
        symbols=SCALING_SYMBOLS,
        cpp_available=True,
        cpu_count=cpu_count,
        points=points,
        note=(
            f"Fixed workload: {SCALING_SYMBOLS} independent RSI-14 computations x "
            f"{rows:,} rows, GIL released around each C++ call, swept across "
            f"thread-pool sizes on a {cpu_count}-core host. Watch for where the "
            "curve flattens - that's the core-count ceiling, not a bug."
        ),
    )


EDGE_CASE_WINDOW = 3
EDGE_CASE_SCENARIOS = ["clean", "leading_nan", "interior_nan", "all_nan"]
EDGE_CASE_KERNELS = ["rolling_std", "rolling_max"]
_EDGE_CASE_BASE = np.array([1.0, 2.0, 3.0, 2.0, 5.0, 4.0, 6.0, 5.0, 7.0, 6.0, 8.0, 7.0])

_EDGE_CASE_NOTES = {
    "rolling_std": (
        "rolling_std was fixed to correctly 'forget' a stale NaN once it exits "
        "the window (see kernels.cpp and the README's Lessons Learned section) - "
        "both NumPy and C++ should match pandas exactly, on every scenario here."
    ),
    "rolling_max": (
        "rolling_max/rolling_min are documented as assuming NaN-free input - in "
        "the real pipeline they're only ever called on raw high/low columns, "
        "which never contain NaN. Feed them one here and watch pandas, NumPy, "
        "and C++ disagree - an honest, currently-true limitation, not a claim."
    ),
}


def _edge_case_input(scenario: str) -> np.ndarray:
    x = _EDGE_CASE_BASE.copy()
    if scenario == "clean":
        return x
    if scenario == "leading_nan":
        x[0] = np.nan
        return x
    if scenario == "interior_nan":
        x[3] = np.nan
        return x
    if scenario == "all_nan":
        return np.full(len(x), np.nan)
    raise HTTPException(400, f"unknown scenario, must be one of {EDGE_CASE_SCENARIOS}")


def _to_list(arr: np.ndarray) -> list[float | None]:
    return [None if np.isnan(v) else round(float(v), 4) for v in arr]


class EdgeCaseResponse(BaseModel):
    scenario: str
    kernel: str
    cpp_available: bool
    input: list[float | None]
    pandas: list[float | None]
    cpp: list[float | None] | None
    numpy: list[float | None]
    cpp_matches_pandas: bool | None
    numpy_matches_pandas: bool
    note: str


@router.get("/edge-case", response_model=EdgeCaseResponse)
def benchmark_edge_case(
    scenario: str = Query(default="leading_nan"),
    kernel: str = Query(default="rolling_std"),
) -> EdgeCaseResponse:
    """Interactive proof, not just a claim: feed the same tiny NaN-containing
    series to pandas, the hand-vectorized NumPy kernel, and the C++ kernel,
    and compare outputs element-by-element."""
    if kernel not in EDGE_CASE_KERNELS:
        raise HTTPException(400, f"unknown kernel, must be one of {EDGE_CASE_KERNELS}")

    x = _edge_case_input(scenario)
    s = pd.Series(x)

    if kernel == "rolling_std":
        pandas_out = s.rolling(EDGE_CASE_WINDOW).std().to_numpy()
        numpy_out = rolling_std_numpy(x, EDGE_CASE_WINDOW)
        cpp_out = ck.rolling_std(x, EDGE_CASE_WINDOW) if CPP_AVAILABLE else None
    else:
        pandas_out = s.rolling(EDGE_CASE_WINDOW, min_periods=1).max().to_numpy()
        numpy_out = rolling_max_numpy(x, EDGE_CASE_WINDOW, 1)
        cpp_out = ck.rolling_max(x, EDGE_CASE_WINDOW, 1) if CPP_AVAILABLE else None

    numpy_matches = bool(np.allclose(numpy_out, pandas_out, equal_nan=True, atol=1e-9))
    cpp_matches = (
        bool(np.allclose(cpp_out, pandas_out, equal_nan=True, atol=1e-9))
        if cpp_out is not None
        else None
    )

    return EdgeCaseResponse(
        scenario=scenario,
        kernel=kernel,
        cpp_available=CPP_AVAILABLE,
        input=_to_list(x),
        pandas=_to_list(pandas_out),
        cpp=_to_list(cpp_out) if cpp_out is not None else None,
        numpy=_to_list(numpy_out),
        cpp_matches_pandas=cpp_matches,
        numpy_matches_pandas=numpy_matches,
        note=_EDGE_CASE_NOTES[kernel],
    )


REAL_BACKTEST_REPS = 3
REAL_BACKTEST_TICKERS = ["AAPL", "NVDA", "TSLA"]


async def _fetch_real_ohlcv(db: AsyncSession, ticker: str) -> pd.DataFrame:
    """Every other benchmark on this page uses a synthetic random walk.
    This one doesn't - it's the platform's own ingested history."""
    result = await db.execute(
        select(
            OHLCVBar.time,
            OHLCVBar.open,
            OHLCVBar.high,
            OHLCVBar.low,
            OHLCVBar.close,
            OHLCVBar.volume,
        )
        .where(OHLCVBar.ticker == ticker.upper(), OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()
    if len(rows) < 300:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Only {len(rows)} daily bars ingested for {ticker.upper()} - need "
                f"300+. Try one of {REAL_BACKTEST_TICKERS}, or ingest more via "
                f"POST /api/v1/market-data/{ticker.upper()}/ingest."
            ),
        )
    idx = pd.DatetimeIndex([r.time for r in rows])
    return pd.DataFrame(
        {
            "open": [float(r.open) for r in rows],
            "high": [float(r.high) for r in rows],
            "low": [float(r.low) for r in rows],
            "close": [float(r.close) for r in rows],
            "volume": [float(r.volume) for r in rows],
        },
        index=idx,
    )


def _macd_entries_exits(feat: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Same crossover rule as run_macd_backtest() in the backtesting engine,
    but fed by the macd_hist column compute_features() already produced -
    proving the real strategy's trade decisions don't change based on which
    kernel backend generated the features underneath it."""
    hist = feat["macd_hist"]
    entries = (hist > 0) & (hist.shift(1) <= 0)
    exits = (hist < 0) & (hist.shift(1) >= 0)
    return entries, exits


class RealBacktestResponse(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    n_bars: int
    n_bars_after_warmup: int
    years: int
    cpp_available: bool
    pandas_ms: float
    cpp_ms: float | None
    speedup: float | None
    max_abs_diff: float | None
    strategy: str
    total_return_pct: float
    annual_return_pct: float
    sharpe_ratio: float
    n_trades: int
    backtest_results_match: bool | None
    note: str


@router.get("/real-backtest", response_model=RealBacktestResponse)
async def benchmark_real_backtest(
    ticker: str = Query(default="AAPL"),
    years: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> RealBacktestResponse:
    """The credibility check: every other endpoint on this page uses a
    synthetic random walk. This one runs compute_features() - pandas vs.
    the C++-backed drop-in - on this platform's own ingested real daily
    history for `ticker`, then feeds a real MACD-crossover backtest
    (backend/app/backtesting/engine.py) from each backend's output to
    confirm the actual trading decision doesn't change, only the time it
    took to get there.

    Windowed to the last `years` years (default 5): the full ingested
    history goes back to 1980 for some tickers, and a long-only strategy
    compounded over 45 years produces an eye-watering, not-useful percentage
    - a recent window is the honest way to keep the number meaningful."""
    increment_run_count()
    full_df = await _fetch_real_ohlcv(db, ticker)
    df = full_df.tail(years * 252)

    def median_ms(fn, reps: int) -> tuple[float, pd.DataFrame]:
        ts = []
        out = None
        for _ in range(reps):
            t0 = time.perf_counter()
            out = fn()
            ts.append((time.perf_counter() - t0) * 1e3)
        assert out is not None
        return float(np.median(ts)), out

    p_ms, p_out = median_ms(lambda: compute_features(df), REAL_BACKTEST_REPS)
    entries, exits = _macd_entries_exits(p_out)
    backtest = _simulate_strategy(
        close=p_out["close"],
        entries=entries,
        exits=exits,
        ticker=ticker.upper(),
        strategy="MACD(12,26,9) Crossover, real features",
    )

    base = {
        "ticker": ticker.upper(),
        "start_date": str(df.index[0])[:10],
        "end_date": str(df.index[-1])[:10],
        "n_bars": len(df),
        "n_bars_after_warmup": len(p_out),
        "years": years,
        "strategy": backtest.strategy,
        "total_return_pct": backtest.total_return_pct,
        "annual_return_pct": backtest.annual_return_pct,
        "sharpe_ratio": backtest.sharpe_ratio,
        "n_trades": backtest.n_trades,
    }

    if not CPP_AVAILABLE:
        return RealBacktestResponse(
            **base,
            cpp_available=False,
            pandas_ms=round(p_ms, 2),
            cpp_ms=None,
            speedup=None,
            max_abs_diff=None,
            backtest_results_match=None,
            note="C++ extension not built on this host; pandas-only timing shown.",
        )

    c_ms, c_out = median_ms(lambda: compute_features_cpp(df), REAL_BACKTEST_REPS)
    compare_cols = ML_FEATURE_COLS + ["target_1d"]
    diff = float((p_out[compare_cols] - c_out[compare_cols]).abs().to_numpy().max())

    c_entries, c_exits = _macd_entries_exits(c_out)
    c_backtest = _simulate_strategy(
        close=c_out["close"],
        entries=c_entries,
        exits=c_exits,
        ticker=ticker.upper(),
        strategy="MACD(12,26,9) Crossover, real features",
    )
    results_match = (
        backtest.total_return_pct == c_backtest.total_return_pct
        and backtest.sharpe_ratio == c_backtest.sharpe_ratio
        and backtest.n_trades == c_backtest.n_trades
    )

    return RealBacktestResponse(
        **base,
        cpp_available=True,
        pandas_ms=round(p_ms, 2),
        cpp_ms=round(c_ms, 2),
        speedup=round(p_ms / c_ms, 1) if c_ms > 0 else None,
        max_abs_diff=diff,
        backtest_results_match=results_match,
        note=(
            f"{len(df):,} real daily bars for {ticker.upper()}, last {years} years "
            f"({base['start_date']} to {base['end_date']}), ingested via yfinance - "
            "not synthetic. The MACD crossover backtest is run twice, once from "
            "pandas-computed features and once from C++-computed features; "
            "backtest_results_match confirms the actual trade decisions are "
            "identical either way."
        ),
    )


class RunCountResponse(BaseModel):
    count: int | None
    note: str


@router.get("/run-count", response_model=RunCountResponse)
def benchmark_run_count() -> RunCountResponse:
    """How many times /kernels, /pipeline, /parallel, /scaling, or
    /real-backtest have been run since this counter last reset (Redis,
    not persisted across a Redis restart/redeploy). None if Redis is
    unreachable - this is a fun-fact counter, not load-bearing."""
    count = get_run_count()
    return RunCountResponse(
        count=count,
        note=(
            "Redis-backed counter, incremented once per benchmark run. "
            "Resets if the Redis instance restarts - it's a fun fact, not "
            "an audit log."
            if count is not None
            else "Redis unreachable on this host - counter unavailable."
        ),
    )
