"""
AEQUITAS - hand-vectorized NumPy kernels, the "middle option" between
pandas and C++ promised in the CppCon abstract's benchmark matrix.

Not used in the production pipeline - built only for the benchmark
endpoints, to answer honestly whether hand-rolled NumPy already gets you
most of the way to the C++ kernels' speedup, or whether pandas' overhead
was never really the bottleneck pandas made it look like.

Techniques used:
  - rolling_std/rolling_max: numpy.lib.stride_tricks.sliding_window_view,
    a zero-copy view over overlapping windows (no Python loop; the
    reduction itself still touches every element, same as pandas).
  - ewm/rsi/atr: the exact same linear recurrence pandas computes
    (y[i] = alpha*x[i] + (1-alpha)*y[i-1]), evaluated as an IIR filter via
    scipy.signal.lfilter (compiled C, not a Python loop) with the initial
    condition solved so y[0] == x[0], matching pandas' adjust=False.
"""

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter


def _ewm_numpy(x: np.ndarray, alpha: float) -> np.ndarray:
    """EWM recurrence y[i] = alpha*x[i] + (1-alpha)*y[i-1], y[0] = x[0]."""
    if len(x) == 0:
        return x.copy()
    zi = [(1.0 - alpha) * x[0]]
    y, _ = lfilter([alpha], [1.0, -(1.0 - alpha)], x, zi=zi)
    return np.asarray(y, dtype=float)


def rolling_std_numpy(x: np.ndarray, window: int) -> np.ndarray:
    n = len(x)
    out = np.full(n, np.nan)
    if n >= window:
        windows = sliding_window_view(x, window)
        out[window - 1 :] = windows.std(axis=1, ddof=1)
    return out


def rolling_max_numpy(x: np.ndarray, window: int, min_periods: int = 1) -> np.ndarray:
    n = len(x)
    out = np.maximum.accumulate(x).astype(float)
    if n >= window:
        windows = sliding_window_view(x, window)
        out[window - 1 :] = windows.max(axis=1)
    if min_periods > 1:
        out[: min_periods - 1] = np.nan
    return out


def ewm_mean_numpy(x: np.ndarray, alpha: float, min_periods: int = 0) -> np.ndarray:
    out = _ewm_numpy(x, alpha)
    if min_periods > 1:
        out[: min_periods - 1] = np.nan
    return out


def rsi_numpy(close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    out = np.full(n, np.nan)
    if n < 2:
        return out

    delta = np.diff(close)
    gain = np.clip(delta, 0, None)
    loss = np.clip(-delta, 0, None)

    alpha = 1.0 / period
    avg_gain = _ewm_numpy(gain, alpha)
    avg_loss = _ewm_numpy(loss, alpha)

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss > 0, avg_gain / avg_loss, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    if len(rsi) >= period - 1:
        rsi[: period - 1] = np.nan

    out[1:] = rsi
    return out


def atr_numpy(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
) -> np.ndarray:
    prev_close = np.empty_like(close)
    prev_close[0] = close[0]
    prev_close[1:] = close[:-1]

    tr = np.maximum.reduce(
        [high - low, np.abs(high - prev_close), np.abs(low - prev_close)]
    )
    tr[0] = high[0] - low[0]

    alpha = 2.0 / (period + 1.0)
    return _ewm_numpy(tr, alpha)
