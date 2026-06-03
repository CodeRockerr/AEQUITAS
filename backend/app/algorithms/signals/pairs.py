"""
AEQUITAS — Pairs trading with cointegration and Kalman filter.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint  # type: ignore[import-untyped]


@dataclass(frozen=True)
class CointegrationResult:
    ticker_a: str
    ticker_b: str
    is_cointegrated: bool
    p_value: float
    hedge_ratio: float
    half_life: float
    interpretation: str


@dataclass(frozen=True)
class PairsSignal:
    ticker_a: str
    ticker_b: str
    spread_zscore: float
    signal: float
    action: str
    hedge_ratio: float
    spread_mean: float
    spread_std: float


def _to_f64(series: pd.Series) -> np.ndarray:
    """Convert pandas Series to plain float64 numpy array."""
    return np.asarray(series.values, dtype=np.float64)


def _ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    """
    Ordinary least squares slope: β = Cov(x,y) / Var(x).

    Replaces np.polyfit to avoid Pylance overload resolution issues.
    Mathematically identical to polyfit(x, y, 1)[0].
    """
    x_dm = x - x.mean()
    y_dm = y - y.mean()
    denom = float(np.dot(x_dm, x_dm))
    if denom == 0.0:
        return 1.0
    return float(np.dot(x_dm, y_dm) / denom)


def check_cointegration(
    prices_a: pd.Series,
    prices_b: pd.Series,
    ticker_a: str = "A",
    ticker_b: str = "B",
    significance: float = 0.05,
) -> CointegrationResult:
    """
    Engle-Granger cointegration test.

    1. OLS: A = β·B + ε
    2. ADF test on residuals ε
    If ε is stationary → pair is cointegrated → spread mean-reverts.
    """
    combined = pd.concat([prices_a, prices_b], axis=1).dropna()
    pa = _to_f64(combined.iloc[:, 0])
    pb = _to_f64(combined.iloc[:, 1])

    coint_result = coint(pa, pb)
    p_value = float(coint_result[1])

    hedge_ratio = _ols_slope(pb, pa)

    spread = pa - hedge_ratio * pb
    spread_series = pd.Series(spread)
    spread_lag = _to_f64(spread_series.shift(1).dropna())
    spread_diff = _to_f64(spread_series.diff().dropna())

    # AR(1) coefficient for half-life calculation
    phi = _ols_slope(spread_lag, spread_diff)

    if phi >= 0 or phi <= -1:
        half_life = float("inf")
    else:
        half_life = float(-np.log(2) / np.log(1.0 + phi))

    is_cointegrated = bool(p_value < significance)
    interp = (
        f"Cointegrated (p={p_value:.4f}). Half-life: {half_life:.1f} days. "
        f"Hedge ratio: {hedge_ratio:.4f}. Spread is mean-reverting."
        if is_cointegrated
        else f"Not cointegrated (p={p_value:.4f}). Spread is not stationary."
    )

    return CointegrationResult(
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        is_cointegrated=is_cointegrated,
        p_value=round(p_value, 6),
        hedge_ratio=round(hedge_ratio, 6),
        half_life=round(half_life, 2),
        interpretation=interp,
    )


def kalman_hedge_ratio(
    prices_a: np.ndarray,
    prices_b: np.ndarray,
    delta: float = 1e-4,
) -> np.ndarray:
    """
    Dynamic hedge ratio via Kalman filter.

    State:       β_t = β_{t-1} + w_t   (random walk)
    Observation: A_t = β_t · B_t + v_t
    """
    n = len(prices_a)
    hedge_ratios = np.zeros(n, dtype=np.float64)
    x = np.zeros(2, dtype=np.float64)
    P = np.eye(2, dtype=np.float64)
    Q = delta * np.eye(2, dtype=np.float64)
    R = np.array([[1.0]], dtype=np.float64)

    for t in range(n):
        pb_t = float(prices_b[t])
        pa_t = float(prices_a[t])
        H = np.array([[pb_t, 1.0]], dtype=np.float64)

        P_pred = P + Q
        innovation = pa_t - float((H @ x).item())
        S = H @ P_pred @ H.T + R
        K = np.asarray(P_pred @ H.T @ np.linalg.inv(S), dtype=np.float64)

        x = np.asarray(x + K.flatten() * innovation, dtype=np.float64)
        P = np.asarray((np.eye(2) - K @ H) @ P_pred, dtype=np.float64)
        hedge_ratios[t] = float(x[0])

    return hedge_ratios


def pairs_signal(
    prices_a: pd.Series,
    prices_b: pd.Series,
    ticker_a: str = "A",
    ticker_b: str = "B",
    entry_zscore: float = 2.0,
    exit_zscore: float = 0.5,
    lookback: int = 60,
    use_kalman: bool = True,
) -> PairsSignal:
    """
    Generate current pairs trading signal using z-score of spread.

    z > +entry → short spread | z < -entry → long spread
    |z| < exit → close position
    """
    combined = pd.concat([prices_a, prices_b], axis=1).dropna()
    pa = _to_f64(combined.iloc[:, 0])
    pb = _to_f64(combined.iloc[:, 1])

    if use_kalman:
        ratios = kalman_hedge_ratio(pa, pb)
        current_hedge = float(ratios[-1])
    else:
        current_hedge = _ols_slope(pb, pa)
        ratios = np.full(len(pa), current_hedge, dtype=np.float64)

    spread = pa - ratios * pb
    spread_series = pd.Series(spread)
    roll_mean = spread_series.rolling(lookback).mean()
    roll_std = spread_series.rolling(lookback).std()
    zscore_series = (spread_series - roll_mean) / roll_std.replace(0.0, np.nan)

    current_zscore = float(zscore_series.iloc[-1])
    spread_mean = float(roll_mean.iloc[-1])
    spread_std = float(roll_std.iloc[-1])

    if current_zscore > entry_zscore:
        sig: float = -1.0
        action = "short_spread"
    elif current_zscore < -entry_zscore:
        sig = 1.0
        action = "long_spread"
    elif abs(current_zscore) < exit_zscore:
        sig = 0.0
        action = "exit"
    else:
        sig = float(-current_zscore / entry_zscore)
        action = "hold"

    return PairsSignal(
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        spread_zscore=round(current_zscore, 4),
        signal=round(sig, 4),
        action=action,
        hedge_ratio=round(current_hedge, 6),
        spread_mean=round(spread_mean, 6),
        spread_std=round(spread_std, 6),
    )
