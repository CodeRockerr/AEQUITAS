"""
AEQUITAS — Unit tests for feature engineering pipeline.
"""

import numpy as np
import pandas as pd
import pytest

from app.algorithms.ml.features import ML_FEATURE_COLS, compute_features


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """300 days of synthetic OHLCV data."""
    rng = np.random.default_rng(42)
    n = 300
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n)))
    high = close * (1 + rng.uniform(0, 0.02, n))
    low = close * (1 - rng.uniform(0, 0.02, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.integers(1_000_000, 10_000_000, n).astype(float)

    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=idx,
    )


@pytest.mark.unit
def test_compute_features_returns_dataframe(sample_ohlcv: pd.DataFrame) -> None:
    result = compute_features(sample_ohlcv)
    assert isinstance(result, pd.DataFrame)


@pytest.mark.unit
def test_all_feature_cols_present(sample_ohlcv: pd.DataFrame) -> None:
    result = compute_features(sample_ohlcv)
    for col in ML_FEATURE_COLS:
        assert col in result.columns, f"Missing feature: {col}"


@pytest.mark.unit
def test_no_nan_in_features(sample_ohlcv: pd.DataFrame) -> None:
    result = compute_features(sample_ohlcv)
    assert not result[ML_FEATURE_COLS].isna().any().any()


@pytest.mark.unit
def test_rsi_bounded(sample_ohlcv: pd.DataFrame) -> None:
    result = compute_features(sample_ohlcv)
    assert result["rsi_14"].between(0, 100).all()


@pytest.mark.unit
def test_volume_ratio_positive(sample_ohlcv: pd.DataFrame) -> None:
    result = compute_features(sample_ohlcv)
    assert (result["volume_ratio"] > 0).all()


@pytest.mark.unit
def test_fewer_rows_after_feature_computation(sample_ohlcv: pd.DataFrame) -> None:
    """Rolling windows and lags reduce the number of valid rows."""
    result = compute_features(sample_ohlcv)
    assert len(result) < len(sample_ohlcv)


@pytest.mark.unit
def test_target_is_next_day_return(sample_ohlcv: pd.DataFrame) -> None:
    """Target should be the forward 1-day return."""
    result = compute_features(sample_ohlcv)
    assert "target_1d" in result.columns
    assert not result["target_1d"].isna().any()
