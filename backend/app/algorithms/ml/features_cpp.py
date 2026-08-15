"""
AEQUITAS — C++-backed feature engineering pipeline.

Drop-in replacement for `compute_features()` (features.py) that routes the
rolling-window and exponential-smoothing primitives through the C++20
kernels (backend/cpp, pybind11) instead of pandas. Column-for-column,
row-for-row identical output — see `test_pipeline_equivalence` in
backend/cpp/test_equivalence.py.

This is the CppCon 2026 poster's "drop-in backend for the full 19-feature
compute_features pipeline." Everything here is pure composition of the
seven existing kernels (rolling_mean/std/max/min, ewm_mean, rsi, atr); no
new C++ was needed once rolling_mean/std were made NaN-aware (see
kernels.cpp) to match pandas' behavior on the leading NaN in return_1d.

Degrades by raising ImportError at import time if the extension isn't
built in this environment — callers (the benchmark endpoint, the
equivalence test) check `CPP_AVAILABLE` first rather than relying on this
raising, so pandas stays the only mandatory path.
"""

import numpy as np
import pandas as pd

try:
    import aequitas_kernels as ck

    CPP_AVAILABLE = True
except ImportError:  # extension not built in this environment
    ck = None
    CPP_AVAILABLE = False


def _series(values: np.ndarray, like: pd.Series) -> pd.Series:
    return pd.Series(values, index=like.index)


def compute_features_cpp(df: pd.DataFrame) -> pd.DataFrame:
    """
    C++-backed equivalent of `compute_features()`. See features.py for the
    feature definitions — this mirrors that function line for line, swapping
    each pandas rolling/ewm call for the matching C++ kernel.
    """
    if not CPP_AVAILABLE:
        raise RuntimeError(
            "aequitas_kernels extension not built in this environment; "
            "build it with `pip install ./cpp` (see backend/cpp/README.md)."
        )

    feat = df.copy()

    close = feat["close"]
    volume = feat["volume"]
    high = feat["high"]
    low = feat["low"]

    # ── Returns (plain NumPy — no kernel needed) ─────────────────
    feat["return_1d"] = np.log(close / close.shift(1))
    feat["return_5d"] = np.log(close / close.shift(5))
    feat["return_21d"] = np.log(close / close.shift(21))

    # ── Momentum ──────────────────────────────────────────────
    feat["rsi_14"] = _series(ck.rsi(close.to_numpy(), 14), close)

    ema_12 = ck.ewm_mean(close.to_numpy(), 2 / 13, 0)
    ema_26 = ck.ewm_mean(close.to_numpy(), 2 / 27, 0)
    macd = ema_12 - ema_26
    feat["macd"] = _series(macd, close)
    feat["macd_signal"] = _series(ck.ewm_mean(macd, 2 / 10, 0), close)
    feat["macd_hist"] = feat["macd"] - feat["macd_signal"]

    # ── Volatility ────────────────────────────────────────────
    # return_1d has a leading NaN (close.shift(1)); rolling_std_impl is
    # NaN-aware so this self-heals exactly like pandas once the window
    # scrolls past index 0.
    ret_1d = feat["return_1d"].to_numpy()
    feat["vol_10d"] = _series(ck.rolling_std(ret_1d, 10), close)
    feat["vol_21d"] = _series(ck.rolling_std(ret_1d, 21), close)
    feat["vol_63d"] = _series(ck.rolling_std(ret_1d, 63), close)
    feat["vol_ratio"] = feat["vol_10d"] / feat["vol_63d"]

    sma_20 = ck.rolling_mean(close.to_numpy(), 20)
    std_20 = ck.rolling_std(close.to_numpy(), 20)
    feat["bb_width"] = _series((2 * std_20) / sma_20, close)
    feat["bb_position"] = _series(
        (close.to_numpy() - (sma_20 - 2 * std_20)) / (4 * std_20), close
    )

    # ── Volume ────────────────────────────────────────────────
    vol_mean_20 = ck.rolling_mean(volume.to_numpy(), 20)
    feat["volume_ratio"] = _series(volume.to_numpy() / vol_mean_20, close)
    feat["log_volume"] = np.log(volume + 1)

    # ── Price levels ──────────────────────────────────────────
    lookback_window = min(252, max(len(feat) - 1, 1))
    high_52w = ck.rolling_max(high.to_numpy(), lookback_window, 1)
    low_52w = ck.rolling_min(low.to_numpy(), lookback_window, 1)
    feat["dist_52w_high"] = _series((close.to_numpy() - high_52w) / high_52w, close)
    feat["dist_52w_low"] = _series((close.to_numpy() - low_52w) / low_52w, close)

    feat["atr_14"] = _series(
        ck.atr(high.to_numpy(), low.to_numpy(), close.to_numpy(), 14), close
    )
    feat["atr_ratio"] = feat["atr_14"] / close

    # ── Target variable ───────────────────────────────────────
    feat["target_1d"] = feat["return_1d"].shift(-1)

    feat = feat.dropna()

    return feat
