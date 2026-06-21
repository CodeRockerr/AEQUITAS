"""
AEQUITAS — Feature engineering pipeline for ML models.

Transforms raw OHLCV data into ML-ready features.
All features are computed from price and volume alone —
no lookahead bias (never use future data to compute past features).

Lookahead bias is the most common mistake in financial ML.
Example of BAD feature: "next day's return" — obviously cheating.
Example of SUBTLE BAD feature: normalising by the full-series mean
— the mean includes future data points.

We avoid this by computing all features using only past data
(rolling windows, lags) with explicit shift() calls.
"""

import numpy as np
import pandas as pd


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute technical features from OHLCV DataFrame.

    Input columns: open, high, low, close, volume
    Output: original columns + engineered features, NaN rows dropped

    All features use only past data — no lookahead bias.

    Args:
        df: DataFrame with OHLCV columns, DatetimeIndex

    Returns:
        DataFrame with features added, NaN rows removed
    """
    feat = df.copy()

    close = feat["close"]
    volume = feat["volume"]
    high = feat["high"]
    low = feat["low"]

    # ── Returns ───────────────────────────────────────────────
    # Log returns: ln(P_t / P_{t-1})
    # Log returns are preferred over simple returns because:
    # 1. They're additive over time
    # 2. They're more normally distributed
    # 3. They prevent negative prices in simulations
    feat["return_1d"] = np.log(close / close.shift(1))
    feat["return_5d"] = np.log(close / close.shift(5))
    feat["return_21d"] = np.log(close / close.shift(21))

    # ── Momentum ──────────────────────────────────────────────
    # RSI (Relative Strength Index): 0-100 oscillator
    # RSI > 70 = overbought, RSI < 30 = oversold
    feat["rsi_14"] = _rsi(close, 14)

    # MACD: difference between 12-day and 26-day EMA
    # Signal line: 9-day EMA of MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    feat["macd"] = ema_12 - ema_26
    feat["macd_signal"] = feat["macd"].ewm(span=9, adjust=False).mean()
    feat["macd_hist"] = feat["macd"] - feat["macd_signal"]

    # ── Volatility ────────────────────────────────────────────
    # Rolling realised volatility: std of log returns
    feat["vol_10d"] = feat["return_1d"].rolling(10).std()
    feat["vol_21d"] = feat["return_1d"].rolling(21).std()
    feat["vol_63d"] = feat["return_1d"].rolling(63).std()

    # Volatility ratio: short-term vs long-term vol
    # > 1 = vol is expanding (regime change signal)
    feat["vol_ratio"] = feat["vol_10d"] / feat["vol_63d"]

    # Bollinger Band width: (upper - lower) / middle
    # Measures how "tight" the bands are — low = consolidation
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    feat["bb_width"] = (2 * std_20) / sma_20
    feat["bb_position"] = (close - (sma_20 - 2 * std_20)) / (4 * std_20)

    # ── Volume ────────────────────────────────────────────────
    # Volume ratio: today's volume vs 20-day average
    # > 1.5 = unusually high volume (institutional activity signal)
    feat["volume_ratio"] = volume / volume.rolling(20).mean()
    feat["log_volume"] = np.log(volume + 1)

    # ── Price levels ──────────────────────────────────────────
    # Distance from 52-week high/low — mean reversion signals
    lookback_window = min(252, max(len(feat) - 1, 1))
    high_52w = high.rolling(lookback_window, min_periods=1).max()
    low_52w = low.rolling(lookback_window, min_periods=1).min()
    feat["dist_52w_high"] = (close - high_52w) / high_52w
    feat["dist_52w_low"] = (close - low_52w) / low_52w

    # Average True Range: measure of daily price range volatility
    feat["atr_14"] = _atr(high, low, close, 14)
    feat["atr_ratio"] = feat["atr_14"] / close  # normalise by price

    # ── Target variable ───────────────────────────────────────
    # Forward 1-day log return: what we're trying to predict
    # .shift(-1) = next day's return
    # Note: we shift(-1) here but drop these rows before training
    # to prevent lookahead bias
    feat["target_1d"] = feat["return_1d"].shift(-1)

    # Drop NaN rows (from rolling windows and shifts)
    feat = feat.dropna()

    return feat


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute RSI using Wilder's smoothing method.

    RSI = 100 - 100 / (1 + RS)
    RS = average gain / average loss over `period` days
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing = EMA with alpha=1/period
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Average True Range.

    True Range = max(
        high - low,
        |high - prev_close|,
        |low - prev_close|
    )
    ATR = EMA of True Range over `period` days
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(span=period, adjust=False).mean()


# Feature columns used for ML training (exclude OHLCV and target)
ML_FEATURE_COLS = [
    "return_1d",
    "return_5d",
    "return_21d",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "vol_10d",
    "vol_21d",
    "vol_63d",
    "vol_ratio",
    "bb_width",
    "bb_position",
    "volume_ratio",
    "log_volume",
    "dist_52w_high",
    "dist_52w_low",
    "atr_14",
    "atr_ratio",
]
