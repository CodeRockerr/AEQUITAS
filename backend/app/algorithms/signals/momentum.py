"""
AEQUITAS — Momentum and mean-reversion signals.

Implements RSI, MACD, and Bollinger Band signals.
All signals return a value in [-1, +1]:
  +1 = strong buy
  -1 = strong sell
   0 = neutral

This normalised scale makes signals composable —
you can average multiple signals into a combined signal.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SignalResult:
    """Output of a signal computation."""

    signal: float  # [-1, +1] normalised signal value
    raw_value: float  # raw indicator value (e.g. RSI=67.3)
    indicator: str  # name of the indicator
    interpretation: str  # human-readable explanation


def rsi_signal(
    close: pd.Series,
    period: int = 14,
    overbought: float = 70,
    oversold: float = 30,
) -> SignalResult:
    """
    RSI (Relative Strength Index) mean-reversion signal.

    RSI measures the speed and magnitude of recent price changes.
    Range: 0-100.
      > overbought (70) → bearish signal (sell)
      < oversold (30)   → bullish signal (buy)
      40-60             → neutral

    The signal is normalised to [-1, +1] by mapping:
      RSI=100 → -1.0 (extreme overbought = strong sell)
      RSI=0   → +1.0 (extreme oversold  = strong buy)
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

    # Normalise: RSI 50 = 0, RSI 0 = +1, RSI 100 = -1
    signal = -(rsi - 50) / 50

    if rsi > overbought:
        interp = f"Overbought (RSI={rsi:.1f}) — bearish mean-reversion signal"
    elif rsi < oversold:
        interp = f"Oversold (RSI={rsi:.1f}) — bullish mean-reversion signal"
    else:
        interp = f"Neutral (RSI={rsi:.1f})"

    return SignalResult(
        signal=round(float(signal), 4),
        raw_value=round(rsi, 2),
        indicator="RSI",
        interpretation=interp,
    )


def macd_signal(
    close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> SignalResult:
    """
    MACD (Moving Average Convergence Divergence) momentum signal.

    MACD = EMA(fast) - EMA(slow)
    Signal line = EMA(MACD, signal_period)
    Histogram = MACD - Signal line

    Trading logic:
      Histogram > 0 and rising → bullish momentum
      Histogram < 0 and falling → bearish momentum
      Zero crossover → momentum shift (strongest signal)

    We use the histogram normalised by price for scale-independence.
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    raw_hist = float(histogram.iloc[-1])
    price = float(close.iloc[-1])

    # Normalise histogram by price level for comparability across stocks
    normalised = raw_hist / price if price > 0 else 0.0

    # Clip to [-1, +1] using a typical histogram range of ±0.5% of price
    signal = float(np.clip(normalised / 0.005, -1.0, 1.0))

    if signal > 0.3:
        interp = f"Bullish momentum (MACD hist={raw_hist:.4f})"
    elif signal < -0.3:
        interp = f"Bearish momentum (MACD hist={raw_hist:.4f})"
    else:
        interp = f"Weak momentum (MACD hist={raw_hist:.4f})"

    return SignalResult(
        signal=round(signal, 4),
        raw_value=round(raw_hist, 6),
        indicator="MACD",
        interpretation=interp,
    )


def bollinger_signal(
    close: pd.Series, period: int = 20, n_std: float = 2.0
) -> SignalResult:
    """
    Bollinger Band mean-reversion signal.

    Upper band = SMA + n_std * σ
    Lower band = SMA - n_std * σ

    The %B indicator measures where price is within the bands:
      %B = (price - lower) / (upper - lower)
      %B > 1.0 → price above upper band → overbought → sell
      %B < 0.0 → price below lower band → oversold → buy
      %B = 0.5 → price at middle band → neutral

    Signal: normalised so %B=1 → -1 (sell) and %B=0 → +1 (buy)
    """
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + n_std * std
    lower = sma - n_std * std

    price = float(close.iloc[-1])
    upper_val = float(upper.iloc[-1])
    lower_val = float(lower.iloc[-1])
    band_width = upper_val - lower_val

    if band_width == 0:
        pct_b = 0.5
    else:
        pct_b = (price - lower_val) / band_width

    # Normalise: %B=0.5 → 0, %B=0 → +1, %B=1 → -1
    signal = float(np.clip(1.0 - 2.0 * pct_b, -1.0, 1.0))

    bb_width_pct = (
        (band_width / float(sma.iloc[-1])) * 100 if float(sma.iloc[-1]) > 0 else 0
    )

    if pct_b > 1.0:
        interp = f"Above upper band (%B={pct_b:.2f}) — overbought"
    elif pct_b < 0.0:
        interp = f"Below lower band (%B={pct_b:.2f}) — oversold"
    else:
        interp = f"Within bands (%B={pct_b:.2f}, width={bb_width_pct:.1f}%)"

    return SignalResult(
        signal=round(signal, 4),
        raw_value=round(pct_b, 4),
        indicator="Bollinger",
        interpretation=interp,
    )


def combined_signal(
    close: pd.Series,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Combine RSI, MACD, and Bollinger signals into one score.

    Default weights give equal weight to each signal.
    You can pass custom weights to emphasise certain signals.

    Returns a dict with individual signals and combined score.
    """
    if weights is None:
        weights = {"RSI": 1 / 3, "MACD": 1 / 3, "Bollinger": 1 / 3}

    rsi = rsi_signal(close)
    macd = macd_signal(close)
    boll = bollinger_signal(close)

    combined = (
        weights.get("RSI", 0) * rsi.signal
        + weights.get("MACD", 0) * macd.signal
        + weights.get("Bollinger", 0) * boll.signal
    )

    if combined > 0.3:
        direction = "bullish"
    elif combined < -0.3:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "combined_signal": round(combined, 4),
        "direction": direction,
        "signals": {
            "rsi": {
                "value": rsi.signal,
                "raw": rsi.raw_value,
                "note": rsi.interpretation,
            },
            "macd": {
                "value": macd.signal,
                "raw": macd.raw_value,
                "note": macd.interpretation,
            },
            "bollinger": {
                "value": boll.signal,
                "raw": boll.raw_value,
                "note": boll.interpretation,
            },
        },
    }
