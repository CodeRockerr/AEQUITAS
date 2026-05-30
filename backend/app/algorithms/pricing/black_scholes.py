"""
AEQUITAS — Black-Scholes options pricing engine.

Implements the Black-Scholes-Merton model for European options.
All functions are pure — no side effects, no database calls.
This makes them trivial to test and reuse across the system.

Reference: Black, F. & Scholes, M. (1973). "The Pricing of Options
and Corporate Liabilities." Journal of Political Economy, 81(3).
"""

import math
from dataclasses import dataclass
from enum import Enum

from scipy.stats import norm  # type: ignore[import-untyped]


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True)
class BlackScholesInputs:
    """
    Validated inputs for the Black-Scholes model.

    frozen=True makes this immutable — inputs can't be changed
    after creation, preventing subtle bugs.
    """

    spot: float  # S — current stock price
    strike: float  # K — option strike price
    rate: float  # r — risk-free interest rate (annualised, e.g. 0.05 = 5%)
    volatility: float  # σ — implied volatility (annualised, e.g. 0.20 = 20%)
    expiry: float  # T — time to expiry in years (e.g. 0.25 = 3 months)
    option_type: OptionType = OptionType.CALL

    def __post_init__(self) -> None:
        """Validate inputs on construction."""
        if self.spot <= 0:
            raise ValueError(f"Spot price must be positive, got {self.spot}")
        if self.strike <= 0:
            raise ValueError(f"Strike price must be positive, got {self.strike}")
        if self.volatility <= 0:
            raise ValueError(f"Volatility must be positive, got {self.volatility}")
        if self.expiry <= 0:
            raise ValueError(f"Expiry must be positive, got {self.expiry}")


@dataclass(frozen=True)
class Greeks:
    """
    The five standard option Greeks.

    Each Greek measures sensitivity of the option price
    to a 1-unit change in the corresponding input.
    """

    delta: float  # ΔC/ΔS — price change per $1 move in spot
    gamma: float  # Δ²C/ΔS² — delta change per $1 move in spot
    vega: float  # ΔC/Δσ — price change per 1% move in volatility
    theta: float  # ΔC/ΔT — price change per 1 calendar day
    rho: float  # ΔC/Δr — price change per 1% move in interest rate


@dataclass(frozen=True)
class BlackScholesResult:
    """Complete output of the Black-Scholes model."""

    price: float
    greeks: Greeks
    d1: float
    d2: float
    inputs: BlackScholesInputs


def _compute_d1_d2(inputs: BlackScholesInputs) -> tuple[float, float]:
    """
    Compute d1 and d2 — the core of Black-Scholes.

    d1 = [ln(S/K) + (r + σ²/2)·T] / (σ·√T)
    d2 = d1 - σ·√T

    These are standardised normal variables used to compute
    the probability that the option expires in-the-money.
    """
    S, K, r, sigma, T = (
        inputs.spot,
        inputs.strike,
        inputs.rate,
        inputs.volatility,
        inputs.expiry,
    )
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return float(d1), float(d2)


def price(inputs: BlackScholesInputs) -> BlackScholesResult:
    """
    Price a European option using Black-Scholes.

    The model assumes:
      - Log-normal distribution of stock prices
      - Constant volatility (the biggest real-world limitation)
      - Continuous trading with no transaction costs
      - No dividends (use Black-76 or adjust for dividends)

    Returns the full result including price and all Greeks.
    """
    S, K, r, sigma, T = (
        inputs.spot,
        inputs.strike,
        inputs.rate,
        inputs.volatility,
        inputs.expiry,
    )
    d1, d2 = _compute_d1_d2(inputs)
    sqrt_T = math.sqrt(T)
    discount = math.exp(-r * T)

    # ── Option price ──────────────────────────────────────────
    if inputs.option_type == OptionType.CALL:
        option_price = float(S * norm.cdf(d1) - K * discount * norm.cdf(d2))
    else:  # PUT
        # Put-call parity: P = K·e^(-rT)·N(-d2) - S·N(-d1)
        option_price = float(K * discount * norm.cdf(-d2) - S * norm.cdf(-d1))

    # ── Greeks ────────────────────────────────────────────────
    # norm.pdf(d1) = standard normal probability density at d1
    pdf_d1 = norm.pdf(d1)

    if inputs.option_type == OptionType.CALL:
        delta = float(norm.cdf(d1))
        rho = float(K * T * discount * norm.cdf(d2)) / 100
        theta = (
            float(
                -(S * pdf_d1 * sigma) / (2 * sqrt_T) - r * K * discount * norm.cdf(d2)
            )
            / 365
        )
    else:
        delta = float(norm.cdf(d1)) - 1
        rho = float(-K * T * discount * norm.cdf(-d2)) / 100
        theta = (
            float(
                -(S * pdf_d1 * sigma) / (2 * sqrt_T) + r * K * discount * norm.cdf(-d2)
            )
            / 365
        )

    gamma = float(pdf_d1) / (S * sigma * sqrt_T)
    vega = float(S * pdf_d1 * sqrt_T) / 100

    greeks = Greeks(
        delta=round(delta, 6),
        gamma=round(gamma, 6),
        vega=round(vega, 6),
        theta=round(theta, 6),
        rho=round(rho, 6),
    )

    return BlackScholesResult(
        price=round(float(option_price), 6),
        greeks=greeks,
        d1=round(float(d1), 6),
        d2=round(float(d2), 6),
        inputs=inputs,
    )


def implied_volatility(
    market_price: float,
    inputs: BlackScholesInputs,
    tolerance: float = 1e-6,
    max_iterations: int = 100,
) -> float:
    """
    Compute implied volatility using Newton-Raphson iteration.

    Implied vol is the volatility that makes the Black-Scholes
    price equal to the observed market price. It's the market's
    consensus forecast of future volatility embedded in option prices.

    Newton-Raphson: σ_new = σ_old - (BS_price - market_price) / vega

    Converges in ~5 iterations for typical inputs.
    Raises ValueError if it doesn't converge (e.g. deep ITM/OTM).
    """
    # Initial guess: use Brenner-Subrahmanyam approximation
    sigma = math.sqrt(2 * math.pi / inputs.expiry) * market_price / inputs.spot

    for _ in range(max_iterations):
        # Price with current sigma estimate
        current_inputs = BlackScholesInputs(
            spot=inputs.spot,
            strike=inputs.strike,
            rate=inputs.rate,
            volatility=sigma,
            expiry=inputs.expiry,
            option_type=inputs.option_type,
        )
        result = price(current_inputs)
        price_diff = result.price - market_price

        if abs(price_diff) < tolerance:
            return round(sigma, 6)

        # vega in actual units (not per 1%)
        vega_actual = result.greeks.vega * 100
        if abs(vega_actual) < 1e-10:
            raise ValueError("Vega too small — option may be deep ITM/OTM")

        # Newton-Raphson update
        sigma = sigma - price_diff / vega_actual

        if sigma <= 0:
            sigma = 1e-6  # floor at near-zero

    raise ValueError(
        f"Implied volatility did not converge after {max_iterations} iterations. "
        f"Last estimate: {sigma:.4f}"
    )
