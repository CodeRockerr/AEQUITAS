"""
AEQUITAS - Equivalence tests for the hand-vectorized NumPy kernels
(features_numpy.py), the "middle option" between pandas and C++.
"""

import numpy as np
import pandas as pd
import pytest

from app.algorithms.ml.features import _atr, _rsi
from app.algorithms.ml.features_numpy import (
    atr_numpy,
    ewm_mean_numpy,
    rolling_max_numpy,
    rolling_std_numpy,
    rsi_numpy,
)


@pytest.fixture
def ohlc():
    rng = np.random.default_rng(42)
    n = 20_000
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    return close, high, low


@pytest.mark.unit
def test_rolling_std_numpy(ohlc):
    close, _, _ = ohlc
    got = rolling_std_numpy(close, 20)
    want = pd.Series(close).rolling(20).std()
    assert np.allclose(got, want, atol=1e-7, equal_nan=True)


@pytest.mark.unit
def test_rolling_std_numpy_leading_nan(ohlc):
    close, _, _ = ohlc
    ret = np.concatenate([[np.nan], np.log(close[1:] / close[:-1])])
    got = rolling_std_numpy(ret, 21)
    want = pd.Series(ret).rolling(21).std()
    assert np.allclose(got, want, atol=1e-7, equal_nan=True)


@pytest.mark.unit
def test_rolling_max_numpy(ohlc):
    _, high, _ = ohlc
    got = rolling_max_numpy(high, 252, 1)
    want = pd.Series(high).rolling(252, min_periods=1).max()
    assert np.allclose(got, want, equal_nan=True)


@pytest.mark.unit
def test_ewm_mean_numpy(ohlc):
    close, _, _ = ohlc
    got = ewm_mean_numpy(close, 2 / 13, 0)
    want = pd.Series(close).ewm(span=12, adjust=False).mean()
    assert np.allclose(got, want, atol=1e-9, equal_nan=True)


@pytest.mark.unit
def test_rsi_numpy(ohlc):
    close, _, _ = ohlc
    got = rsi_numpy(close, 14)
    want = _rsi(pd.Series(close), 14)
    assert np.allclose(got, want, atol=1e-6, equal_nan=True)


@pytest.mark.unit
def test_atr_numpy(ohlc):
    close, high, low = ohlc
    got = atr_numpy(high, low, close, 14)
    want = _atr(pd.Series(high), pd.Series(low), pd.Series(close), 14)
    assert np.allclose(got, want, atol=1e-9, equal_nan=True)
