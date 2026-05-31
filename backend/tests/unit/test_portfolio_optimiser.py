"""
AEQUITAS — Unit tests for portfolio optimiser.
"""

import numpy as np
import pytest

from app.algorithms.portfolio.optimiser import (
    efficient_frontier,
    maximum_sharpe,
    minimum_variance,
)

# Reproducible synthetic returns: 3 assets, 2 years daily
RNG = np.random.default_rng(42)
RETURNS = RNG.multivariate_normal(
    mean=[0.0005, 0.0004, 0.0003],
    cov=[
        [0.0004, 0.0001, 0.00005],
        [0.0001, 0.0003, 0.00008],
        [0.00005, 0.00008, 0.0002],
    ],
    size=504,
)
TICKERS = ["AAPL", "MSFT", "SPY"]


@pytest.mark.unit
def test_max_sharpe_weights_sum_to_one() -> None:
    """Portfolio weights must sum to 1."""
    result = maximum_sharpe(RETURNS, TICKERS)
    assert abs(sum(result.weights) - 1.0) < 1e-6


@pytest.mark.unit
def test_max_sharpe_weights_non_negative() -> None:
    """No short selling — all weights must be >= 0."""
    result = maximum_sharpe(RETURNS, TICKERS)
    assert all(w >= -1e-6 for w in result.weights)


@pytest.mark.unit
def test_max_sharpe_tickers_match() -> None:
    """Returned tickers must match input."""
    result = maximum_sharpe(RETURNS, TICKERS)
    assert result.tickers == TICKERS


@pytest.mark.unit
def test_max_sharpe_positive_sharpe() -> None:
    """With positive expected returns, Sharpe ratio should be positive."""
    result = maximum_sharpe(RETURNS, TICKERS)
    assert result.sharpe_ratio > 0


@pytest.mark.unit
def test_min_variance_lower_vol_than_max_sharpe() -> None:
    """Minimum variance portfolio should have lower volatility than max Sharpe."""
    mv = minimum_variance(RETURNS, TICKERS)
    ms = maximum_sharpe(RETURNS, TICKERS)
    assert mv.volatility <= ms.volatility + 1e-6


@pytest.mark.unit
def test_min_variance_weights_sum_to_one() -> None:
    result = minimum_variance(RETURNS, TICKERS)
    assert abs(sum(result.weights) - 1.0) < 1e-6


@pytest.mark.unit
def test_efficient_frontier_returns_multiple_points() -> None:
    """Efficient frontier should return multiple portfolios."""
    frontier = efficient_frontier(RETURNS, TICKERS, n_points=10)
    assert len(frontier) >= 5


@pytest.mark.unit
def test_efficient_frontier_increasing_return() -> None:
    """Frontier portfolios should have generally increasing expected returns."""
    frontier = efficient_frontier(RETURNS, TICKERS, n_points=10)
    returns = [p.expected_return for p in frontier]
    assert returns[-1] > returns[0]
