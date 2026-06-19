"""
AEQUITAS — Unit tests for Fama-French and execution algorithms.
"""

import numpy as np
import pandas as pd
import pytest

from app.algorithms.execution.twap_vwap import (
    analyse_execution,
    default_volume_profile,
    implementation_shortfall_schedule,
    twap_schedule,
    vwap_schedule,
)
from app.algorithms.signals.factor_model import FactorModelResult, run_factor_model

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def return_series() -> pd.Series:
    rng = np.random.default_rng(42)
    n = 250
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.Series(rng.normal(0.0005, 0.015, n), index=idx)


@pytest.fixture
def factor_returns(return_series: pd.Series) -> dict:
    rng = np.random.default_rng(7)
    n = len(return_series)
    idx = return_series.index
    return {
        "market": pd.Series(rng.normal(0.0004, 0.012, n), index=idx),
        "small": pd.Series(rng.normal(0.0003, 0.014, n), index=idx),
        "value": pd.Series(rng.normal(0.0003, 0.011, n), index=idx),
        "growth": pd.Series(rng.normal(0.0004, 0.013, n), index=idx),
    }


# ── Fama-French tests ─────────────────────────────────────────


@pytest.mark.unit
def test_factor_model_returns_result(
    return_series: pd.Series, factor_returns: dict
) -> None:
    result = run_factor_model(
        return_series,
        factor_returns["market"],
        factor_returns["small"],
        factor_returns["value"],
        factor_returns["growth"],
        ticker="TEST",
    )
    assert isinstance(result, FactorModelResult)


@pytest.mark.unit
def test_factor_model_r_squared_bounded(
    return_series: pd.Series, factor_returns: dict
) -> None:
    result = run_factor_model(
        return_series,
        factor_returns["market"],
        factor_returns["small"],
        factor_returns["value"],
        factor_returns["growth"],
    )
    assert 0.0 <= result.r_squared <= 1.0


@pytest.mark.unit
def test_factor_model_market_beta_finite(
    return_series: pd.Series, factor_returns: dict
) -> None:
    result = run_factor_model(
        return_series,
        factor_returns["market"],
        factor_returns["small"],
        factor_returns["value"],
        factor_returns["growth"],
    )
    assert np.isfinite(result.beta_market)


@pytest.mark.unit
def test_factor_model_high_beta_stock() -> None:
    rng = np.random.default_rng(0)
    n = 300
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    mkt = pd.Series(rng.normal(0.0005, 0.01, n), index=idx)
    stock = mkt * 2.0 + pd.Series(rng.normal(0, 0.002, n), index=idx)
    small = pd.Series(rng.normal(0.0003, 0.01, n), index=idx)
    value = pd.Series(rng.normal(0.0003, 0.01, n), index=idx)
    growth = pd.Series(rng.normal(0.0004, 0.01, n), index=idx)
    result = run_factor_model(stock, mkt, small, value, growth)
    assert 1.5 < result.beta_market < 2.5


@pytest.mark.unit
def test_factor_model_alpha_tstat_finite(
    return_series: pd.Series, factor_returns: dict
) -> None:
    result = run_factor_model(
        return_series,
        factor_returns["market"],
        factor_returns["small"],
        factor_returns["value"],
        factor_returns["growth"],
    )
    assert np.isfinite(result.alpha_tstat)


@pytest.mark.unit
def test_factor_model_interpretation_nonempty(
    return_series: pd.Series, factor_returns: dict
) -> None:
    result = run_factor_model(
        return_series,
        factor_returns["market"],
        factor_returns["small"],
        factor_returns["value"],
        factor_returns["growth"],
    )
    assert len(result.interpretation) > 0


@pytest.mark.unit
def test_factor_model_insufficient_data_raises() -> None:
    rng = np.random.default_rng(0)
    n = 30
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    s = pd.Series(rng.normal(0, 0.01, n), index=idx)
    with pytest.raises(ValueError, match="60"):
        run_factor_model(s, s, s, s, s)


# ── Volume profile ────────────────────────────────────────────


@pytest.mark.unit
def test_volume_profile_sums_to_one() -> None:
    assert abs(default_volume_profile(13).sum() - 1.0) < 1e-9


@pytest.mark.unit
def test_volume_profile_u_shaped() -> None:
    p = default_volume_profile(13)
    assert p[:2].mean() > p[5:8].mean()
    assert p[-2:].mean() > p[5:8].mean()


# ── TWAP ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_twap_total_shares_exact() -> None:
    assert sum(s.shares for s in twap_schedule("AAPL", 10_000, 13).slices) == 10_000


@pytest.mark.unit
def test_twap_equal_distribution() -> None:
    shares = [s.shares for s in twap_schedule("AAPL", 13_000, 13).slices]
    assert max(shares) - min(shares) <= 1


@pytest.mark.unit
def test_twap_correct_n_intervals() -> None:
    assert len(twap_schedule("AAPL", 5_000, 8).slices) == 8


@pytest.mark.unit
def test_twap_algorithm_label() -> None:
    assert twap_schedule("AAPL", 1_000).algorithm == "TWAP"


# ── VWAP ─────────────────────────────────────────────────────


@pytest.mark.unit
def test_vwap_total_shares_exact() -> None:
    assert sum(s.shares for s in vwap_schedule("AAPL", 10_000, 13).slices) == 10_000


@pytest.mark.unit
def test_vwap_front_and_back_heavier() -> None:
    shares = [s.shares for s in vwap_schedule("AAPL", 100_000, 13).slices]
    assert np.mean(shares[:2]) > np.mean(shares[5:8])
    assert np.mean(shares[-2:]) > np.mean(shares[5:8])


@pytest.mark.unit
def test_vwap_algorithm_label() -> None:
    assert vwap_schedule("AAPL", 1_000).algorithm == "VWAP"


@pytest.mark.unit
def test_vwap_custom_flat_profile() -> None:
    shares = [
        s.shares
        for s in vwap_schedule("AAPL", 13_000, 13, volume_profile=np.ones(13)).slices
    ]
    assert max(shares) - min(shares) <= 1


# ── Implementation Shortfall ──────────────────────────────────


@pytest.mark.unit
def test_is_total_shares_exact() -> None:
    assert (
        sum(s.shares for s in implementation_shortfall_schedule("AAPL", 10_000).slices)
        == 10_000
    )


@pytest.mark.unit
def test_is_high_urgency_front_loaded() -> None:
    shares = [
        s.shares
        for s in implementation_shortfall_schedule("AAPL", 100_000, urgency=1.0).slices
    ]
    assert shares[0] > shares[-1]


@pytest.mark.unit
def test_is_low_urgency_flat() -> None:
    shares = [
        s.shares
        for s in implementation_shortfall_schedule("AAPL", 100_000, urgency=0.0).slices
    ]
    assert max(shares) - min(shares) <= 2


@pytest.mark.unit
def test_is_urgency_clipped() -> None:
    s1 = implementation_shortfall_schedule("AAPL", 1_000, urgency=2.0)
    s2 = implementation_shortfall_schedule("AAPL", 1_000, urgency=-1.0)
    assert sum(s.shares for s in s1.slices) == 1_000
    assert sum(s.shares for s in s2.slices) == 1_000


# ── Execution analysis ────────────────────────────────────────


@pytest.mark.unit
def test_analyse_execution_returns_result() -> None:
    schedule = twap_schedule("AAPL", 1_000, n_intervals=4)
    result = analyse_execution(
        schedule, 150.0, [150.0, 150.5, 151.0, 150.8], [150.1, 150.4, 151.1, 150.7]
    )
    assert np.isfinite(result.implementation_shortfall_bps)


@pytest.mark.unit
def test_analyse_execution_perfect_fill_near_zero_is() -> None:
    schedule = twap_schedule("AAPL", 1_000, n_intervals=4)
    prices = [100.0, 100.0, 100.0, 100.0]
    result = analyse_execution(schedule, 100.0, prices, prices)
    assert abs(result.implementation_shortfall_bps) < 0.01


@pytest.mark.unit
def test_analyse_execution_mismatched_raises() -> None:
    schedule = twap_schedule("AAPL", 1_000, n_intervals=4)
    with pytest.raises(ValueError):
        analyse_execution(schedule, 100.0, [100.0, 101.0], [100.0, 101.0])
