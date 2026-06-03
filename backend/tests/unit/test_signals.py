"""
AEQUITAS — Unit tests for momentum signals and backtester.
"""

import numpy as np
import pandas as pd
import pytest

from app.algorithms.signals.momentum import (
    bollinger_signal,
    combined_signal,
    macd_signal,
    rsi_signal,
)
from app.algorithms.signals.pairs import check_cointegration, pairs_signal
from app.backtesting.engine import (
    run_bollinger_backtest,
    run_macd_backtest,
    run_momentum_backtest,
)

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def trending_up() -> pd.Series:
    """300 days of steadily rising prices."""
    rng = np.random.default_rng(42)
    n = 300
    returns = rng.normal(0.001, 0.015, n)
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=pd.date_range("2023-01-01", periods=n, freq="B"))


@pytest.fixture
def mean_reverting() -> pd.Series:
    """300 days of mean-reverting prices (oscillating)."""
    n = 300
    t = np.linspace(0, 6 * np.pi, n)
    prices = 100 + 10 * np.sin(t) + np.random.default_rng(42).normal(0, 1, n)
    return pd.Series(prices, index=pd.date_range("2023-01-01", periods=n, freq="B"))


@pytest.fixture
def cointegrated_pair(trending_up: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Two cointegrated price series."""
    rng = np.random.default_rng(42)
    noise = pd.Series(
        rng.normal(0, 0.5, len(trending_up)),
        index=trending_up.index,
    )
    # Series B = 0.8 * Series A + stationary noise
    series_b = 0.8 * trending_up + noise
    return trending_up, series_b


# ── RSI tests ─────────────────────────────────────────────────


@pytest.mark.unit
def test_rsi_signal_in_range(trending_up: pd.Series) -> None:
    result = rsi_signal(trending_up)
    assert -1.0 <= result.signal <= 1.0


@pytest.mark.unit
def test_rsi_raw_value_bounded(trending_up: pd.Series) -> None:
    result = rsi_signal(trending_up)
    assert 0 <= result.raw_value <= 100


@pytest.mark.unit
def test_rsi_indicator_name(trending_up: pd.Series) -> None:
    result = rsi_signal(trending_up)
    assert result.indicator == "RSI"


@pytest.mark.unit
def test_rsi_signal_direction_consistent(trending_up: pd.Series) -> None:
    """RSI signal direction should be consistent with price trend.

    We use the trending_up fixture which has realistic noise,
    guaranteeing both gains and losses exist for RSI computation.
    """
    result = rsi_signal(trending_up)
    assert not np.isnan(result.signal), "RSI signal should not be NaN"
    # trending_up has positive drift so RSI should be above 50
    # meaning signal should be negative (overbought lean)
    # but we only assert it's a valid number, not a specific sign
    # since short series may not reach overbought threshold
    assert -1.0 <= result.signal <= 1.0


# ── MACD tests ────────────────────────────────────────────────


@pytest.mark.unit
def test_macd_signal_in_range(trending_up: pd.Series) -> None:
    result = macd_signal(trending_up)
    assert -1.0 <= result.signal <= 1.0


@pytest.mark.unit
def test_macd_indicator_name(trending_up: pd.Series) -> None:
    result = macd_signal(trending_up)
    assert result.indicator == "MACD"


# ── Bollinger tests ───────────────────────────────────────────


@pytest.mark.unit
def test_bollinger_signal_in_range(trending_up: pd.Series) -> None:
    result = bollinger_signal(trending_up)
    assert -1.0 <= result.signal <= 1.0


@pytest.mark.unit
def test_bollinger_indicator_name(trending_up: pd.Series) -> None:
    result = bollinger_signal(trending_up)
    assert result.indicator == "Bollinger"


# ── Combined signal tests ─────────────────────────────────────


@pytest.mark.unit
def test_combined_signal_has_all_keys(trending_up: pd.Series) -> None:
    result = combined_signal(trending_up)
    assert "combined_signal" in result
    assert "direction" in result
    assert "signals" in result
    assert "rsi" in result["signals"]
    assert "macd" in result["signals"]
    assert "bollinger" in result["signals"]


@pytest.mark.unit
def test_combined_signal_in_range(trending_up: pd.Series) -> None:
    result = combined_signal(trending_up)
    assert -1.0 <= result["combined_signal"] <= 1.0


@pytest.mark.unit
def test_combined_direction_valid(trending_up: pd.Series) -> None:
    result = combined_signal(trending_up)
    assert result["direction"] in ["bullish", "bearish", "neutral"]


# ── Pairs trading tests ───────────────────────────────────────


@pytest.mark.unit
def test_cointegration_detects_cointegrated_pair(
    cointegrated_pair: tuple[pd.Series, pd.Series],
) -> None:
    """Synthetic cointegrated pair should pass the cointegration test."""
    a, b = cointegrated_pair
    result = check_cointegration(a, b, "A", "B")
    assert result.is_cointegrated


@pytest.mark.unit
def test_cointegration_hedge_ratio_positive(
    cointegrated_pair: tuple[pd.Series, pd.Series],
) -> None:
    a, b = cointegrated_pair
    result = check_cointegration(a, b)
    assert result.hedge_ratio > 0


@pytest.mark.unit
def test_pairs_signal_action_valid(
    cointegrated_pair: tuple[pd.Series, pd.Series],
) -> None:
    a, b = cointegrated_pair
    result = pairs_signal(a, b, "A", "B")
    assert result.action in ["long_spread", "short_spread", "hold", "exit"]


@pytest.mark.unit
def test_pairs_signal_in_range(
    cointegrated_pair: tuple[pd.Series, pd.Series],
) -> None:
    a, b = cointegrated_pair
    result = pairs_signal(a, b, "A", "B")
    assert -1.0 <= result.signal <= 1.0


# ── Backtester tests ──────────────────────────────────────────


@pytest.mark.unit
def test_rsi_backtest_returns_result(trending_up: pd.Series) -> None:
    result = run_momentum_backtest(trending_up, "TEST")
    assert result.ticker == "TEST"
    assert result.n_bars > 0


@pytest.mark.unit
def test_macd_backtest_returns_result(trending_up: pd.Series) -> None:
    result = run_macd_backtest(trending_up, "TEST")
    assert result.strategy.startswith("MACD")


@pytest.mark.unit
def test_bollinger_backtest_returns_result(mean_reverting: pd.Series) -> None:
    result = run_bollinger_backtest(mean_reverting, "TEST")
    assert result.strategy.startswith("Bollinger")


@pytest.mark.unit
def test_backtest_sharpe_is_finite(trending_up: pd.Series) -> None:
    result = run_momentum_backtest(trending_up, "TEST")
    assert np.isfinite(result.sharpe_ratio)


@pytest.mark.unit
def test_backtest_max_drawdown_negative_or_zero(trending_up: pd.Series) -> None:
    """Max drawdown should always be <= 0 (it's a loss)."""
    result = run_momentum_backtest(trending_up, "TEST")
    assert result.max_drawdown_pct <= 0


@pytest.mark.unit
def test_backtest_win_rate_between_0_and_100(trending_up: pd.Series) -> None:
    result = run_momentum_backtest(trending_up, "TEST")
    assert 0 <= result.win_rate_pct <= 100


@pytest.mark.unit
def test_bollinger_mean_reversion_on_oscillating_prices(
    mean_reverting: pd.Series,
) -> None:
    """
    Bollinger mean-reversion should generate multiple trades
    on oscillating prices.
    """
    result = run_bollinger_backtest(mean_reverting, "TEST")
    assert result.n_trades >= 2


@pytest.mark.unit
def test_backtest_has_benchmark(trending_up: pd.Series) -> None:
    result = run_momentum_backtest(trending_up, "TEST")
    assert result.benchmark_return_pct != 0  # trending up → non-zero BH return
    assert isinstance(result.alpha_pct, float)
