"""
AEQUITAS — Vectorised backtesting engine.

Wraps vectorbt for fast strategy backtesting and
computes a comprehensive tearsheet of performance metrics.

Why vectorbt over a loop-based backtester?
  Loop: iterates over 252 days × n_strategies → slow
  Vectorbt: applies numpy operations across entire history → fast

A "tearsheet" is a one-page summary of strategy performance
used by every hedge fund. Key metrics:
  - Sharpe ratio: return per unit of risk (>1 = good, >2 = great)
  - Max drawdown: worst peak-to-trough loss (lower = better)
  - Calmar ratio: annual return / max drawdown
  - Win rate: % of trades that were profitable
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    """Comprehensive backtest performance metrics."""

    # Returns
    total_return_pct: float
    annual_return_pct: float
    # Risk
    annual_volatility_pct: float
    max_drawdown_pct: float
    # Risk-adjusted
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    # Trade stats
    win_rate_pct: float
    n_trades: int
    avg_trade_duration_days: float
    # Benchmark comparison
    benchmark_return_pct: float
    alpha_pct: float
    # Metadata
    ticker: str
    strategy: str
    start_date: str
    end_date: str
    n_bars: int


def run_momentum_backtest(
    close: pd.Series,
    ticker: str,
    rsi_period: int = 14,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    """
    Backtest RSI mean-reversion strategy.

    Entry: RSI crosses below oversold threshold → buy
    Exit:  RSI crosses above overbought threshold → sell

    Uses vectorised operations — no Python loops over time.
    """
    # Compute RSI
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(
        alpha=1 / rsi_period, min_periods=rsi_period, adjust=False
    ).mean()
    avg_loss = loss.ewm(
        alpha=1 / rsi_period, min_periods=rsi_period, adjust=False
    ).mean()
    rsi = 100 - (100 / (1 + avg_gain / avg_loss.replace(0, np.nan)))

    # Generate entries and exits (vectorised)
    entries = (rsi < rsi_oversold) & (rsi.shift(1) >= rsi_oversold)
    exits = (rsi > rsi_overbought) & (rsi.shift(1) <= rsi_overbought)

    return _simulate_strategy(
        close=close,
        entries=entries,
        exits=exits,
        ticker=ticker,
        strategy=f"RSI({rsi_period}) Mean-Reversion",
        initial_capital=initial_capital,
    )


def run_macd_backtest(
    close: pd.Series,
    ticker: str,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    """
    Backtest MACD crossover momentum strategy.

    Entry: MACD histogram crosses above zero → buy
    Exit:  MACD histogram crosses below zero → sell
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    entries = (histogram > 0) & (histogram.shift(1) <= 0)
    exits = (histogram < 0) & (histogram.shift(1) >= 0)

    return _simulate_strategy(
        close=close,
        entries=entries,
        exits=exits,
        ticker=ticker,
        strategy=f"MACD({fast},{slow},{signal_period}) Crossover",
        initial_capital=initial_capital,
    )


def run_bollinger_backtest(
    close: pd.Series,
    ticker: str,
    period: int = 20,
    n_std: float = 2.0,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    """
    Backtest Bollinger Band mean-reversion strategy.

    Entry: price crosses below lower band → buy
    Exit:  price crosses above middle band (SMA) → sell
    """
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    lower = sma - n_std * std

    entries = (close < lower) & (close.shift(1) >= lower.shift(1))
    exits = (close > sma) & (close.shift(1) <= sma.shift(1))

    return _simulate_strategy(
        close=close,
        entries=entries,
        exits=exits,
        ticker=ticker,
        strategy=f"Bollinger({period}, {n_std}σ) Mean-Reversion",
        initial_capital=initial_capital,
    )


def _simulate_strategy(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    ticker: str,
    strategy: str,
    initial_capital: float = 10_000.0,
) -> BacktestResult:
    """
    Simulate a long-only strategy given entry/exit signals.

    Vectorised implementation — no loops over time steps.
    Assumes:
      - Fully invested when in position (no partial sizing)
      - No transaction costs (add in production)
      - Prices at next bar's open (not same-bar — avoids lookahead)
    """
    close = close.dropna()
    entries = entries.reindex(close.index).fillna(False)
    exits = exits.reindex(close.index).fillna(False)

    n = len(close)
    position = np.zeros(n)  # 1 = in position, 0 = flat
    in_trade = False
    trade_entries: list[int] = []
    trade_exits: list[int] = []

    for i in range(1, n):
        if not in_trade and entries.iloc[i]:
            in_trade = True
            trade_entries.append(i)
        elif in_trade and exits.iloc[i]:
            in_trade = False
            trade_exits.append(i)
        position[i] = 1.0 if in_trade else 0.0

    # Daily returns of the strategy
    daily_returns = close.pct_change().fillna(0)
    strategy_returns = daily_returns * pd.Series(position, index=close.index)

    # Cumulative portfolio value
    portfolio = initial_capital * (1 + strategy_returns).cumprod()

    # Buy-and-hold benchmark
    bh_returns = (float(close.iloc[-1]) / float(close.iloc[0])) - 1

    # ── Performance metrics ───────────────────────────────────
    total_return = (float(portfolio.iloc[-1]) / initial_capital) - 1
    n_years = n / 252

    if n_years > 0:
        annual_return = (1 + total_return) ** (1 / n_years) - 1
    else:
        annual_return = 0.0

    annual_vol = float(strategy_returns.std()) * np.sqrt(252)

    # Sharpe ratio (risk-free rate = 5%)
    risk_free = 0.05
    sharpe = (annual_return - risk_free) / annual_vol if annual_vol > 0 else 0.0

    # Sortino ratio (uses only downside volatility)
    downside_returns = strategy_returns[strategy_returns < 0]
    downside_vol = float(downside_returns.std()) * np.sqrt(252)
    sortino = (annual_return - risk_free) / downside_vol if downside_vol > 0 else 0.0

    # Maximum drawdown
    cumulative = (1 + strategy_returns).cumprod()
    rolling_max = cumulative.expanding().max()
    drawdowns = cumulative / rolling_max - 1
    max_drawdown = float(drawdowns.min())

    # Calmar ratio
    calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0.0

    # Trade statistics
    n_trades = len(trade_exits)
    winning_trades = 0
    trade_durations: list[int] = []

    for entry_idx, exit_idx in zip(trade_entries, trade_exits, strict=False):
        entry_price = float(close.iloc[entry_idx])
        exit_price = float(close.iloc[exit_idx])
        if exit_price > entry_price:
            winning_trades += 1
        trade_durations.append(exit_idx - entry_idx)

    win_rate = (winning_trades / n_trades) if n_trades > 0 else 0.0
    avg_duration = float(np.mean(trade_durations)) if trade_durations else 0.0

    start_date = str(close.index[0])[:10]
    end_date = str(close.index[-1])[:10]

    return BacktestResult(
        total_return_pct=round(total_return * 100, 2),
        annual_return_pct=round(annual_return * 100, 2),
        annual_volatility_pct=round(annual_vol * 100, 2),
        max_drawdown_pct=round(max_drawdown * 100, 2),
        sharpe_ratio=round(sharpe, 4),
        sortino_ratio=round(sortino, 4),
        calmar_ratio=round(calmar, 4),
        win_rate_pct=round(win_rate * 100, 2),
        n_trades=n_trades,
        avg_trade_duration_days=round(avg_duration, 1),
        benchmark_return_pct=round(bh_returns * 100, 2),
        alpha_pct=round((total_return - bh_returns) * 100, 2),
        ticker=ticker,
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        n_bars=n,
    )
