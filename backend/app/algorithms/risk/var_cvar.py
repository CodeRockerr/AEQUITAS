"""
AEQUITAS — VaR and CVaR risk engine.
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class VaRResult:
    var: float
    cvar: float
    confidence_level: float
    horizon_days: int
    method: str
    portfolio_value: float


def historical_var(
    returns: NDArray[np.float64],
    portfolio_value: float,
    confidence_level: float = 0.95,
    horizon_days: int = 1,
) -> VaRResult:
    """
    Historical simulation VaR and CVaR.

    Sorts past returns worst-to-best, takes the (1-confidence) percentile
    as VaR, and the mean of all losses beyond that as CVaR.
    No distribution assumption — captures real fat tails and skewness.
    """
    if len(returns) < 30:
        raise ValueError(f"Need at least 30 return observations, got {len(returns)}.")

    sorted_returns = np.sort(returns)
    var_index = int((1 - confidence_level) * len(sorted_returns))
    var_return = float(sorted_returns[var_index])
    sqrt_horizon = math.sqrt(horizon_days)
    var_dollar = abs(var_return * sqrt_horizon) * portfolio_value

    tail_returns = sorted_returns[:var_index]
    if len(tail_returns) == 0:
        cvar_dollar = var_dollar
    else:
        cvar_return = float(np.mean(tail_returns)) * sqrt_horizon
        cvar_dollar = abs(cvar_return) * portfolio_value

    return VaRResult(
        var=round(var_dollar, 2),
        cvar=round(cvar_dollar, 2),
        confidence_level=confidence_level,
        horizon_days=horizon_days,
        method="historical",
        portfolio_value=portfolio_value,
    )


def parametric_var(
    returns: NDArray[np.float64],
    portfolio_value: float,
    confidence_level: float = 0.95,
    horizon_days: int = 1,
) -> VaRResult:
    """
    Parametric (variance-covariance) VaR.

    Assumes normally distributed returns.
    VaR = μ - z·σ where z is the normal quantile.
    Faster than historical but underestimates fat tails.
    """
    from scipy.stats import norm  # type: ignore[import-untyped]

    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    z = float(norm.ppf(1 - confidence_level))
    sqrt_horizon = math.sqrt(horizon_days)

    var_return = mu * horizon_days + z * sigma * sqrt_horizon
    var_dollar = abs(min(var_return, 0)) * portfolio_value

    pdf_z = float(norm.pdf(norm.ppf(1 - confidence_level)))
    cvar_return = -(
        mu * horizon_days - sigma * sqrt_horizon * pdf_z / (1 - confidence_level)
    )
    cvar_dollar = abs(cvar_return) * portfolio_value

    return VaRResult(
        var=round(var_dollar, 2),
        cvar=round(cvar_dollar, 2),
        confidence_level=confidence_level,
        horizon_days=horizon_days,
        method="parametric",
        portfolio_value=portfolio_value,
    )


def montecarlo_var(
    returns: NDArray[np.float64],
    portfolio_value: float,
    confidence_level: float = 0.95,
    horizon_days: int = 1,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> VaRResult:
    """
    Monte Carlo VaR.

    Simulates n_simulations random return paths using estimated
    mean and volatility. seed=42 ensures reproducibility —
    required for audit trails in financial systems.
    """
    rng = np.random.default_rng(seed)
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))

    simulated = rng.normal(
        loc=mu * horizon_days,
        scale=sigma * math.sqrt(horizon_days),
        size=n_simulations,
    )
    simulated_sorted = np.sort(simulated)
    var_index = int((1 - confidence_level) * n_simulations)

    var_return = float(simulated_sorted[var_index])
    var_dollar = abs(min(var_return, 0)) * portfolio_value

    tail_returns = simulated_sorted[:var_index]
    cvar_return = float(np.mean(tail_returns)) if len(tail_returns) > 0 else var_return
    cvar_dollar = abs(min(cvar_return, 0)) * portfolio_value

    return VaRResult(
        var=round(var_dollar, 2),
        cvar=round(cvar_dollar, 2),
        confidence_level=confidence_level,
        horizon_days=horizon_days,
        method="montecarlo",
        portfolio_value=portfolio_value,
    )
