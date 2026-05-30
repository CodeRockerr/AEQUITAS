"""
AEQUITAS — Mean-variance portfolio optimiser.

Markowitz (1952): for a given expected return, there exists a portfolio
with minimum variance. The set of all such portfolios is the efficient frontier.

Sharpe ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
Higher Sharpe = better risk-adjusted return.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize  # type: ignore[import-untyped]


@dataclass(frozen=True)
class PortfolioMetrics:
    weights: list[float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    tickers: list[str]


def _portfolio_stats(
    weights: NDArray[np.float64],
    mean_returns: NDArray[np.float64],
    cov_matrix: NDArray[np.float64],
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> tuple[float, float, float]:
    """
    Annualised return, volatility, and Sharpe for a weight vector.

    Annualisation: multiply daily return by 252, volatility by √252.
    This assumes i.i.d. (independent, identically distributed) daily returns.
    """
    port_return = float(np.dot(weights, mean_returns)) * trading_days
    port_variance = float(weights.T @ cov_matrix @ weights) * trading_days
    port_volatility = float(np.sqrt(port_variance))
    sharpe = (
        (port_return - risk_free_rate) / port_volatility if port_volatility > 0 else 0.0
    )
    return port_return, port_volatility, sharpe


def _prepare_inputs(
    returns_matrix: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Compute mean returns and covariance matrix, both as float64.
    Explicit dtype cast silences Pylance's floating[Any] warnings.
    """
    mean_returns = np.mean(returns_matrix, axis=0).astype(np.float64)
    cov_matrix = np.cov(returns_matrix.T).astype(np.float64)
    return mean_returns, cov_matrix


def maximum_sharpe(
    returns_matrix: NDArray[np.float64],
    tickers: list[str],
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> PortfolioMetrics:
    """
    Find the portfolio with the maximum Sharpe ratio (tangency portfolio).

    This is the single best risk/return tradeoff on the efficient frontier.
    Uses SLSQP (Sequential Least Squares Programming) optimisation.
    Constraints: weights sum to 1, each weight in [0, 1] (no shorting).
    """
    n_assets = returns_matrix.shape[1]
    mean_returns, cov_matrix = _prepare_inputs(returns_matrix)

    def neg_sharpe(weights: NDArray[np.float64]) -> float:
        _, _, sharpe = _portfolio_stats(
            weights, mean_returns, cov_matrix, risk_free_rate, trading_days
        )
        return -sharpe

    constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w)) - 1}]
    bounds = [(0.0, 1.0)] * n_assets
    w0 = np.ones(n_assets, dtype=np.float64) / n_assets

    result = minimize(
        neg_sharpe,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 1000},
    )

    if not result.success:
        raise ValueError(f"Optimisation failed: {result.message}")

    weights = result.x.astype(np.float64)
    ret, vol, sharpe = _portfolio_stats(
        weights, mean_returns, cov_matrix, risk_free_rate, trading_days
    )

    return PortfolioMetrics(
        weights=[round(float(w), 6) for w in weights],
        expected_return=round(ret, 6),
        volatility=round(vol, 6),
        sharpe_ratio=round(sharpe, 6),
        tickers=tickers,
    )


def minimum_variance(
    returns_matrix: NDArray[np.float64],
    tickers: list[str],
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> PortfolioMetrics:
    """
    Find the minimum variance portfolio.

    The leftmost point on the efficient frontier — lowest possible
    risk regardless of return. Useful for risk-averse allocators.
    """
    n_assets = returns_matrix.shape[1]
    mean_returns, cov_matrix = _prepare_inputs(returns_matrix)

    def portfolio_variance(weights: NDArray[np.float64]) -> float:
        return float(weights.T @ cov_matrix @ weights)

    constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w)) - 1}]
    bounds = [(0.0, 1.0)] * n_assets
    w0 = np.ones(n_assets, dtype=np.float64) / n_assets

    result = minimize(
        portfolio_variance,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 1000},
    )

    if not result.success:
        raise ValueError(f"Optimisation failed: {result.message}")

    weights = result.x.astype(np.float64)
    ret, vol, sharpe = _portfolio_stats(
        weights, mean_returns, cov_matrix, risk_free_rate, trading_days
    )

    return PortfolioMetrics(
        weights=[round(float(w), 6) for w in weights],
        expected_return=round(ret, 6),
        volatility=round(vol, 6),
        sharpe_ratio=round(sharpe, 6),
        tickers=tickers,
    )


def efficient_frontier(
    returns_matrix: NDArray[np.float64],
    tickers: list[str],
    n_points: int = 50,
    risk_free_rate: float = 0.05,
    trading_days: int = 252,
) -> list[PortfolioMetrics]:
    """
    Generate n_points portfolios tracing the efficient frontier.

    Each point is the minimum-variance portfolio for a target return.
    Together they form the curve the frontend dashboard will plot.
    """
    n_assets = returns_matrix.shape[1]
    mean_returns, cov_matrix = _prepare_inputs(returns_matrix)

    min_ret = float(np.min(mean_returns)) * trading_days
    max_ret = float(np.max(mean_returns)) * trading_days
    target_returns = np.linspace(min_ret, max_ret, n_points)

    frontier: list[PortfolioMetrics] = []

    for target in target_returns:

        def portfolio_variance(weights: NDArray[np.float64]) -> float:
            return float(weights.T @ cov_matrix @ weights)

        constraints = [
            {"type": "eq", "fun": lambda w: float(np.sum(w)) - 1},
            {
                "type": "eq",
                "fun": lambda w, t=float(target): (
                    float(np.dot(w, mean_returns)) * trading_days - t
                ),
            },
        ]
        bounds = [(0.0, 1.0)] * n_assets
        w0 = np.ones(n_assets, dtype=np.float64) / n_assets

        result = minimize(
            portfolio_variance,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if result.success:
            weights = result.x.astype(np.float64)
            ret, vol, sharpe = _portfolio_stats(
                weights, mean_returns, cov_matrix, risk_free_rate, trading_days
            )
            frontier.append(
                PortfolioMetrics(
                    weights=[round(float(w), 6) for w in weights],
                    expected_return=round(ret, 6),
                    volatility=round(vol, 6),
                    sharpe_ratio=round(sharpe, 6),
                    tickers=tickers,
                )
            )

    return frontier
