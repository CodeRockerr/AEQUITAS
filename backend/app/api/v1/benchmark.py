"""
AEQUITAS — Live Python vs C++ kernel benchmark.

GET /api/v1/benchmark/kernels?rows=100000

Runs the pandas implementations from features.py head-to-head against
the C++ kernels (backend/cpp, pybind11) on identical synthetic OHLCV
data, and returns median wall-clock timings plus numerical agreement.

Degrades gracefully: if the extension isn't built in this deployment,
`cpp_available` is false and only pandas timings are returned.

Rows are capped to keep the endpoint cheap enough for the free-tier
Render deployment.
"""

import time

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.algorithms.ml.features import _atr, _rsi

try:
    import aequitas_kernels as ck

    CPP_AVAILABLE = True
except ImportError:  # extension not built in this environment
    ck = None
    CPP_AVAILABLE = False

router = APIRouter(prefix="/api/v1/benchmark")

MAX_ROWS = 500_000
REPS = 5


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
