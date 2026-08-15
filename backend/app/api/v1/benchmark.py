"""
AEQUITAS — Live Python vs C++ kernel benchmark.

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
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.algorithms.ml.features import ML_FEATURE_COLS, _atr, _rsi, compute_features
from app.algorithms.ml.features_cpp import CPP_AVAILABLE, compute_features_cpp

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
    """Synthetic OHLCV DataFrame for pipeline/parallel benchmarks — a
    geometric random walk, same shape as the real market data compute_features
    expects (open/high/low/close/volume, DatetimeIndex)."""
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, rows)))
    high = close * (1 + rng.uniform(0, 0.02, rows))
    low = close * (1 - rng.uniform(0, 0.02, rows))
    open_ = close * (1 + rng.normal(0, 0.005, rows))
    volume = rng.integers(1_000_000, 10_000_000, rows).astype(float)
    idx = pd.date_range("2010-01-01", periods=rows, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


class KernelResult(BaseModel):
    kernel: str
    description: str
    pandas_ms: float
    cpp_ms: float | None
    speedup: float | None
    max_abs_diff: float | None  # numerical agreement, None if C++ missing


class BenchmarkResponse(BaseModel):
    rows: int
    reps: int
    cpp_available: bool
    note: str
    results: list[KernelResult]


def _median_ms(fn, reps: int = REPS) -> tuple[float, np.ndarray]:
    """Median wall-clock ms over `reps` runs; returns (ms, last_result)."""
    out = None
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        out = fn()
        ts.append((time.perf_counter() - t0) * 1e3)
    return float(np.median(ts)), np.asarray(out, dtype=float)


@router.get("/kernels", response_model=BenchmarkResponse)
def benchmark_kernels(
    rows: int = Query(default=100_000, ge=1_000, le=MAX_ROWS),
) -> BenchmarkResponse:
    # Deterministic synthetic OHLCV — geometric random walk
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
            (lambda: ck.rolling_std(close, 21)) if ck else None,
        ),
        (
            "rolling_max_252",
            "52-week high (rolling max, min_periods=1)",
            lambda: hs.rolling(252, min_periods=1).max(),
            (lambda: ck.rolling_max(high, 252, 1)) if ck else None,
        ),
        (
            "ewm_span_12",
            "12-day EMA (MACD building block)",
            lambda: s.ewm(span=12, adjust=False).mean(),
            (lambda: ck.ewm_mean(close, 2 / 13, 0)) if ck else None,
        ),
        (
            "rsi_14",
            "RSI-14, Wilder smoothing",
            lambda: _rsi(s, 14),
            (lambda: ck.rsi(close, 14)) if ck else None,
        ),
        (
            "atr_14",
            "Average True Range 14",
            lambda: _atr(hs, ls, s, 14),
            (lambda: ck.atr(high, low, close, 14)) if ck else None,
        ),
    ]

    results: list[KernelResult] = []
    for name, desc, pfn, cfn in cases:
        p_ms, p_out = _median_ms(pfn)
        if cfn is not None:
            c_ms, c_out = _median_ms(cfn)
            diff = float(np.nanmax(np.abs(p_out - c_out)))
            results.append(
                KernelResult(
                    kernel=name,
                    description=desc,
                    pandas_ms=round(p_ms, 3),
                    cpp_ms=round(c_ms, 3),
                    speedup=round(p_ms / c_ms, 1) if c_ms > 0 else None,
                    max_abs_diff=diff,
                )
            )
        else:
            results.append(
                KernelResult(
                    kernel=name,
                    description=desc,
                    pandas_ms=round(p_ms, 3),
                    cpp_ms=None,
                    speedup=None,
                    max_abs_diff=None,
                )
            )

    return BenchmarkResponse(
        rows=rows,
        reps=REPS,
        cpp_available=CPP_AVAILABLE,
        note=(
            "Timings are median wall-clock over "
            f"{REPS} runs on the API host; identical synthetic OHLCV inputs. "
            "max_abs_diff is the largest absolute deviation between the "
            "pandas and C++ outputs (NaN positions must match)."
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
    each kernel call — the poster's headline result. Parallel speedup is
    bounded by the API host's core count, which is why cpu_count is
    reported alongside it."""
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
    cpu_count = os.cpu_count() or 1

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
    with ThreadPoolExecutor(max_workers=symbols) as ex:
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
            "the API host — it will be far smaller on a 1-2 vCPU deployment than "
            "on an 8-core dev machine."
        ),
    )
