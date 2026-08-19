"""
AEQUITAS - Smoke tests for the extended benchmark endpoints: NumPy
middle-ground comparison, thread-count scaling sweep, and the NaN
edge-case explorer.
"""

import pandas as pd
import pytest

from app.algorithms.ml.features_cpp import CPP_AVAILABLE
from app.api.v1.benchmark import (
    _macd_entries_exits,
    benchmark_edge_case,
    benchmark_kernels,
    benchmark_scaling,
)

pytestmark = pytest.mark.skipif(
    not CPP_AVAILABLE, reason="aequitas_kernels extension not built"
)


@pytest.mark.unit
def test_kernels_includes_numpy_and_memory_fields() -> None:
    r = benchmark_kernels(rows=5_000)
    for result in r.results:
        assert result.numpy_ms is not None
        assert result.numpy_max_abs_diff is not None
        assert result.pandas_peak_kb > 0
        assert result.cpp_peak_kb is not None


@pytest.mark.unit
def test_scaling_sweep_returns_all_thread_counts() -> None:
    r = benchmark_scaling(rows=10_000)
    assert [p.threads for p in r.points] == [1, 2, 4, 8]
    assert all(p.ms > 0 for p in r.points)


@pytest.mark.unit
@pytest.mark.parametrize(
    "scenario", ["clean", "leading_nan", "interior_nan", "all_nan"]
)
def test_edge_case_rolling_std_always_matches_pandas(scenario: str) -> None:
    # rolling_std was fixed to be NaN-safe on every scenario.
    r = benchmark_edge_case(scenario=scenario, kernel="rolling_std")
    assert r.cpp_matches_pandas is True
    assert r.numpy_matches_pandas is True


@pytest.mark.unit
def test_edge_case_rolling_max_known_limitation() -> None:
    # rolling_max/min are documented as NaN-unsafe - this pins down that
    # honestly-disclosed limitation as a regression check, not a silent bug.
    clean = benchmark_edge_case(scenario="clean", kernel="rolling_max")
    assert clean.cpp_matches_pandas is True

    with_nan = benchmark_edge_case(scenario="interior_nan", kernel="rolling_max")
    assert with_nan.cpp_matches_pandas is False


@pytest.mark.unit
def test_macd_entries_exits_matches_backtest_engine_rule() -> None:
    # Same crossover rule as run_macd_backtest() in the backtesting engine,
    # just fed by an already-computed macd_hist column instead of
    # recomputing MACD inline - this pins down that they stay in sync.
    hist = pd.Series([-1.0, -0.5, 0.5, 1.0, 0.5, -0.5, -1.0])
    feat = pd.DataFrame({"macd_hist": hist})

    entries, exits = _macd_entries_exits(feat)

    assert entries.tolist() == [False, False, True, False, False, False, False]
    assert exits.tolist() == [False, False, False, False, False, True, False]
