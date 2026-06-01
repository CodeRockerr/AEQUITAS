"""
AEQUITAS — Unit tests for HMM regime detector.
"""

import numpy as np
import pytest

from app.algorithms.ml.regime_detector import (
    detect_regimes,
    fit_regime_model,
)

# Synthetic returns: 3 clear regimes
RNG = np.random.default_rng(42)
BULL_RETURNS = RNG.normal(0.001, 0.008, 200)
BEAR_RETURNS = RNG.normal(-0.001, 0.012, 150)
HIGH_VOL_RETURNS = RNG.normal(0.0, 0.025, 100)
ALL_RETURNS = np.concatenate([BULL_RETURNS, BEAR_RETURNS, HIGH_VOL_RETURNS])


@pytest.fixture
def fitted_model():
    return fit_regime_model(ALL_RETURNS, n_regimes=3)


@pytest.mark.unit
def test_fit_returns_fitted_hmm(fitted_model) -> None:
    assert fitted_model.model is not None
    assert fitted_model.n_regimes == 3


@pytest.mark.unit
def test_regime_map_has_all_regimes(fitted_model) -> None:
    regime_values = set(fitted_model.regime_map.values())
    assert len(regime_values) == 3


@pytest.mark.unit
def test_score_is_finite(fitted_model) -> None:
    assert np.isfinite(fitted_model.score)


@pytest.mark.unit
def test_detect_regimes_correct_length(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    assert len(result.regimes) == len(ALL_RETURNS)
    assert len(result.regime_labels) == len(ALL_RETURNS)


@pytest.mark.unit
def test_regime_probs_sum_to_one(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    for probs in result.regime_probs:
        assert abs(sum(probs) - 1.0) < 1e-4


@pytest.mark.unit
def test_current_regime_is_valid(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    assert result.current_regime_label in ["Bull", "Bear", "High Volatility"]


@pytest.mark.unit
def test_current_regime_prob_between_0_and_1(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    assert 0 <= result.current_regime_prob <= 1


@pytest.mark.unit
def test_transition_matrix_rows_sum_to_one(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    for row in result.transition_matrix:
        assert abs(sum(row) - 1.0) < 1e-4


@pytest.mark.unit
def test_regime_stats_all_regimes_present(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    for label in ["Bull", "Bear", "High Volatility"]:
        assert label in result.regime_stats


@pytest.mark.unit
def test_regime_stats_pct_sums_to_100(fitted_model) -> None:
    result = detect_regimes(fitted_model, ALL_RETURNS)
    total_pct = sum(stats["pct_of_time"] for stats in result.regime_stats.values())
    assert abs(total_pct - 100.0) < 1.0
