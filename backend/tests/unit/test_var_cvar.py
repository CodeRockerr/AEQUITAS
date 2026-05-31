"""
AEQUITAS — Unit tests for VaR and CVaR risk engine.
"""

import numpy as np
import pytest

from app.algorithms.risk.var_cvar import (
    historical_var,
    montecarlo_var,
    parametric_var,
)

# Reproducible test returns: 2 years of simulated daily returns
RNG = np.random.default_rng(42)
RETURNS = RNG.normal(loc=0.0005, scale=0.015, size=504)  # ~2yr daily
PORTFOLIO_VALUE = 100_000.0


@pytest.mark.unit
def test_historical_var_positive() -> None:
    """VaR must always be a positive dollar amount."""
    result = historical_var(RETURNS, PORTFOLIO_VALUE)
    assert result.var > 0


@pytest.mark.unit
def test_historical_cvar_gte_var() -> None:
    """CVaR must always be >= VaR — it's the expected loss beyond VaR."""
    result = historical_var(RETURNS, PORTFOLIO_VALUE)
    assert result.cvar >= result.var


@pytest.mark.unit
def test_higher_confidence_higher_var() -> None:
    """99% VaR should be larger than 95% VaR."""
    var_95 = historical_var(RETURNS, PORTFOLIO_VALUE, confidence_level=0.95)
    var_99 = historical_var(RETURNS, PORTFOLIO_VALUE, confidence_level=0.99)
    assert var_99.var >= var_95.var


@pytest.mark.unit
def test_longer_horizon_higher_var() -> None:
    """10-day VaR should be larger than 1-day VaR (square-root-of-time)."""
    var_1d = historical_var(RETURNS, PORTFOLIO_VALUE, horizon_days=1)
    var_10d = historical_var(RETURNS, PORTFOLIO_VALUE, horizon_days=10)
    assert var_10d.var > var_1d.var


@pytest.mark.unit
def test_larger_portfolio_larger_var() -> None:
    """Doubling portfolio value should double VaR."""
    var_small = historical_var(RETURNS, 100_000.0)
    var_large = historical_var(RETURNS, 200_000.0)
    assert abs(var_large.var - 2 * var_small.var) < 1.0  # within $1


@pytest.mark.unit
def test_historical_var_method_label() -> None:
    result = historical_var(RETURNS, PORTFOLIO_VALUE)
    assert result.method == "historical"


@pytest.mark.unit
def test_parametric_var_positive() -> None:
    result = parametric_var(RETURNS, PORTFOLIO_VALUE)
    assert result.var > 0
    assert result.cvar >= result.var
    assert result.method == "parametric"


@pytest.mark.unit
def test_montecarlo_var_positive() -> None:
    result = montecarlo_var(RETURNS, PORTFOLIO_VALUE, seed=42)
    assert result.var > 0
    assert result.cvar >= result.var
    assert result.method == "montecarlo"


@pytest.mark.unit
def test_montecarlo_reproducible() -> None:
    """Same seed should produce identical results."""
    r1 = montecarlo_var(RETURNS, PORTFOLIO_VALUE, seed=42)
    r2 = montecarlo_var(RETURNS, PORTFOLIO_VALUE, seed=42)
    assert r1.var == r2.var
    assert r1.cvar == r2.cvar


@pytest.mark.unit
def test_insufficient_data_raises() -> None:
    """Historical VaR should reject fewer than 30 observations."""
    short_returns = np.array([0.01, -0.02, 0.005] * 5)  # only 15 obs
    with pytest.raises(ValueError, match="30"):
        historical_var(short_returns, PORTFOLIO_VALUE)


@pytest.mark.unit
def test_all_three_methods_reasonable_range() -> None:
    """
    All three methods should produce VaR in a similar ballpark.
    For normally distributed returns they should be close.
    We verify they're all within 3x of each other.
    """
    h = historical_var(RETURNS, PORTFOLIO_VALUE)
    p = parametric_var(RETURNS, PORTFOLIO_VALUE)
    m = montecarlo_var(RETURNS, PORTFOLIO_VALUE, seed=42)

    values = [h.var, p.var, m.var]
    assert max(values) / min(values) < 3.0, (
        f"Methods diverged too much: historical={h.var:.0f}, "
        f"parametric={p.var:.0f}, montecarlo={m.var:.0f}"
    )
