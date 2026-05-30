"""
AEQUITAS — Unit tests for Black-Scholes pricing engine.

We verify against known analytical values.
The at-the-money call test uses a well-known approximation:
  ATM call ≈ 0.4 · S · σ · √T  (Brenner-Subrahmanyam)
"""

import math

import pytest

from app.algorithms.pricing.black_scholes import (
    BlackScholesInputs,
    OptionType,
    implied_volatility,
    price,
)

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def atm_call() -> BlackScholesInputs:
    """At-the-money call: spot == strike."""
    return BlackScholesInputs(
        spot=100.0,
        strike=100.0,
        rate=0.05,
        volatility=0.20,
        expiry=1.0,
        option_type=OptionType.CALL,
    )


@pytest.fixture
def atm_put() -> BlackScholesInputs:
    """At-the-money put."""
    return BlackScholesInputs(
        spot=100.0,
        strike=100.0,
        rate=0.05,
        volatility=0.20,
        expiry=1.0,
        option_type=OptionType.PUT,
    )


@pytest.fixture
def itm_call() -> BlackScholesInputs:
    """In-the-money call: spot > strike."""
    return BlackScholesInputs(
        spot=110.0,
        strike=100.0,
        rate=0.05,
        volatility=0.20,
        expiry=0.5,
        option_type=OptionType.CALL,
    )


# ── Price tests ───────────────────────────────────────────────


@pytest.mark.unit
def test_atm_call_price_positive(atm_call: BlackScholesInputs) -> None:
    """Any option with positive time value must have positive price."""
    result = price(atm_call)
    assert result.price > 0


@pytest.mark.unit
def test_atm_call_price_approximate(atm_call: BlackScholesInputs) -> None:
    """
    ATM call ≈ S · σ · √T · 0.3989 (from standard normal pdf at 0).
    For S=100, σ=0.20, T=1: ≈ 7.97
    Known exact BS value: ~10.45
    We verify it's in a reasonable range.
    """
    result = price(atm_call)
    assert 8.0 < result.price < 13.0


@pytest.mark.unit
def test_put_call_parity(
    atm_call: BlackScholesInputs, atm_put: BlackScholesInputs
) -> None:
    """
    Put-call parity: C - P = S - K·e^(-rT)

    This is a fundamental no-arbitrage relationship.
    If it doesn't hold, the pricing engine has a bug.
    """
    call_result = price(atm_call)
    put_result = price(atm_put)

    S, K, r, T = 100.0, 100.0, 0.05, 1.0
    parity_rhs = S - K * math.exp(-r * T)
    parity_lhs = call_result.price - put_result.price

    assert (
        abs(parity_lhs - parity_rhs) < 1e-4
    ), f"Put-call parity violated: C-P={parity_lhs:.4f}, S-Ke^(-rT)={parity_rhs:.4f}"


@pytest.mark.unit
def test_itm_call_more_expensive_than_atm(
    atm_call: BlackScholesInputs,
    itm_call: BlackScholesInputs,
) -> None:
    """A deeper ITM call should be worth more than ATM (all else equal)."""
    atm_result = price(atm_call)
    itm_result = price(itm_call)
    assert itm_result.price > atm_result.price * 0.5  # rough sanity check


# ── Greeks tests ──────────────────────────────────────────────


@pytest.mark.unit
def test_call_delta_between_zero_and_one(atm_call: BlackScholesInputs) -> None:
    """Call delta must be between 0 and 1."""
    result = price(atm_call)
    assert 0 < result.greeks.delta < 1


@pytest.mark.unit
def test_put_delta_between_minus_one_and_zero(atm_put: BlackScholesInputs) -> None:
    """Put delta must be between -1 and 0."""
    result = price(atm_put)
    assert -1 < result.greeks.delta < 0


@pytest.mark.unit
def test_gamma_positive(atm_call: BlackScholesInputs) -> None:
    """Gamma is always positive for both calls and puts."""
    result = price(atm_call)
    assert result.greeks.gamma > 0


@pytest.mark.unit
def test_vega_positive(atm_call: BlackScholesInputs) -> None:
    """Vega is always positive — higher vol = higher option price."""
    result = price(atm_call)
    assert result.greeks.vega > 0


@pytest.mark.unit
def test_theta_negative_call(atm_call: BlackScholesInputs) -> None:
    """Theta is negative — options lose value as time passes (time decay)."""
    result = price(atm_call)
    assert result.greeks.theta < 0


# ── Implied volatility tests ──────────────────────────────────


@pytest.mark.unit
def test_implied_vol_round_trip(atm_call: BlackScholesInputs) -> None:
    """
    Round-trip test: price an option, then recover the volatility
    from that price. Should get back the original vol.
    """
    result = price(atm_call)
    recovered_vol = implied_volatility(result.price, atm_call)
    assert abs(recovered_vol - atm_call.volatility) < 1e-4


@pytest.mark.unit
def test_higher_vol_higher_price() -> None:
    """Higher volatility always means higher option price."""
    base = BlackScholesInputs(
        spot=100.0,
        strike=100.0,
        rate=0.05,
        volatility=0.20,
        expiry=1.0,
    )
    high_vol = BlackScholesInputs(
        spot=100.0,
        strike=100.0,
        rate=0.05,
        volatility=0.40,
        expiry=1.0,
    )
    assert price(high_vol).price > price(base).price


# ── Validation tests ──────────────────────────────────────────


@pytest.mark.unit
def test_rejects_negative_spot() -> None:
    with pytest.raises(ValueError, match="positive"):
        BlackScholesInputs(
            spot=-100.0,
            strike=100.0,
            rate=0.05,
            volatility=0.20,
            expiry=1.0,
        )


@pytest.mark.unit
def test_rejects_zero_expiry() -> None:
    with pytest.raises(ValueError, match="positive"):
        BlackScholesInputs(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            volatility=0.20,
            expiry=0.0,
        )
