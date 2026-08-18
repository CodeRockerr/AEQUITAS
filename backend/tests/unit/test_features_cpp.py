"""
AEQUITAS - Equivalence test for the C++-backed feature pipeline.

Verifies compute_features_cpp() (features_cpp.py, C++20 kernels) produces
the same DataFrame as compute_features() (features.py, pandas) on
identical OHLCV input. Skipped when the aequitas_kernels extension isn't
built in this environment (see backend/cpp/README.md).
"""

import numpy as np
import pandas as pd
import pytest

from app.algorithms.ml.features import ML_FEATURE_COLS, compute_features
from app.algorithms.ml.features_cpp import CPP_AVAILABLE, compute_features_cpp

pytestmark = pytest.mark.skipif(
    not CPP_AVAILABLE, reason="aequitas_kernels extension not built"
)


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """2,000 days of synthetic OHLCV data - long enough to exercise every
    rolling window (up to 252 days) well past its warm-up period."""
    rng = np.random.default_rng(7)
    n = 2_000
    close = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.015, n)))
    high = close * (1 + rng.uniform(0, 0.02, n))
    low = close * (1 - rng.uniform(0, 0.02, n))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.integers(1_000_000, 10_000_000, n).astype(float)

    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


@pytest.mark.unit
def test_pipeline_equivalence(sample_ohlcv: pd.DataFrame) -> None:
    pandas_out = compute_features(sample_ohlcv)
    cpp_out = compute_features_cpp(sample_ohlcv)

    assert list(pandas_out.index) == list(cpp_out.index)

    for col in ML_FEATURE_COLS + ["target_1d"]:
        diff = (pandas_out[col] - cpp_out[col]).abs().max()
        assert diff < 1e-6, f"{col}: max abs diff {diff:.3e} exceeds tolerance"
