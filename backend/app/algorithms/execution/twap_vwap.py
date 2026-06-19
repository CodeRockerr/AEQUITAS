"""
AEQUITAS — Execution algorithms: TWAP, VWAP, Implementation Shortfall.

These are the algorithms used by institutional traders to break large
orders into smaller pieces to minimise market impact.

Why does execution matter?
  If you want to buy 100,000 shares of AAPL, placing one order
  will move the price against you (market impact). Execution
  algorithms slice the order over time or volume to minimise this.

TWAP — Time-Weighted Average Price
  Split the order equally over N time intervals.
  Simple, predictable, used when you want to track time.

VWAP — Volume-Weighted Average Price
  Split the order proportionally to expected intraday volume.
  Since volume follows a U-shape (high at open/close, low midday),
  VWAP schedules more shares at open and close.
  Benchmark: your execution is "good" if you beat the day's VWAP.

Implementation Shortfall (IS)
  Minimise the difference between the decision price (when you
  decided to trade) and the actual average execution price.
  Uses an urgency parameter — trade faster if the stock is moving
  against you (higher urgency = more front-loaded).
"""

from dataclasses import dataclass
from typing import cast

import numpy as np


@dataclass(frozen=True)
class ExecutionSlice:
    """A single time slice of an execution schedule."""

    interval: int  # slice index (0-based)
    start_time: str  # e.g. "09:30"
    end_time: str  # e.g. "10:00"
    shares: int  # shares to execute in this slice
    pct_of_order: float  # fraction of total order


@dataclass(frozen=True)
class ExecutionSchedule:
    """
    Full execution schedule for an order.

    Tells the trader: at each time interval, how many shares
    to buy/sell to minimise market impact.
    """

    ticker: str
    total_shares: int
    n_intervals: int
    algorithm: str  # "TWAP" | "VWAP" | "IS"
    slices: list[ExecutionSlice]
    expected_completion: str
    participation_rate: float  # avg % of market volume per interval


@dataclass(frozen=True)
class ExecutionAnalysis:
    """
    Post-trade execution quality analysis.

    Compares how well you executed vs the benchmark.
    """

    algorithm: str
    total_shares: int
    avg_execution_price: float
    vwap_benchmark: float
    implementation_shortfall_bps: float  # basis points vs decision price
    market_impact_bps: float
    participation_rate: float
    interpretation: str


def default_volume_profile(n_intervals: int) -> np.ndarray:
    """
    Generate a U-shaped intraday volume profile.

    Real intraday volume follows a U-shape:
      - High volume at market open (9:30-10:30)
      - Low volume midday (11:30-14:00)
      - High volume at close (14:30-16:00)

    This is well-documented in market microstructure literature.
    We model it as the sum of two half-Gaussians centred at
    the open and close.
    """
    t = np.linspace(0, 1, n_intervals)
    # Two Gaussians: open peak and close peak
    open_peak = np.exp(-0.5 * ((t - 0.0) / 0.2) ** 2)
    close_peak = np.exp(-0.5 * ((t - 1.0) / 0.2) ** 2)
    profile = open_peak + close_peak + 0.15  # 0.15 = flat midday floor
    # Normalise to sum to 1
    return cast(np.ndarray, profile / profile.sum())


def _interval_times(n_intervals: int) -> list[tuple[str, str]]:
    """Generate time labels for each interval (9:30 to 16:00)."""
    market_open = 9 * 60 + 30  # 9:30 in minutes
    market_close = 16 * 60  # 16:00 in minutes
    total_minutes = market_close - market_open
    interval_minutes = total_minutes / n_intervals

    times = []
    for i in range(n_intervals):
        start_min = market_open + i * interval_minutes
        end_min = market_open + (i + 1) * interval_minutes

        start_h, start_m = int(start_min // 60), int(start_min % 60)
        end_h, end_m = int(end_min // 60), int(end_min % 60)

        times.append(
            (
                f"{start_h:02d}:{start_m:02d}",
                f"{end_h:02d}:{end_m:02d}",
            )
        )
    return times


def twap_schedule(
    ticker: str,
    total_shares: int,
    n_intervals: int = 13,  # 30-minute intervals across 6.5-hour day
    avg_daily_volume: int = 50_000_000,
) -> ExecutionSchedule:
    """
    TWAP — Time-Weighted Average Price execution schedule.

    Splits the order equally across all time intervals.
    Each interval gets: total_shares / n_intervals shares.

    When to use:
      - Order size is small relative to daily volume
      - You want predictable, systematic execution
      - You don't have a view on intraday price direction

    Args:
        total_shares:       total order size
        n_intervals:        number of time slices (default: 13 × 30-min)
        avg_daily_volume:   expected daily volume for participation rate
    """
    shares_per_interval = total_shares / n_intervals
    times = _interval_times(n_intervals)
    interval_volume = avg_daily_volume / n_intervals

    slices = []
    remaining = total_shares
    for i, (start, end) in enumerate(times):
        is_last = i == n_intervals - 1
        shares = remaining if is_last else round(shares_per_interval)
        remaining -= shares
        slices.append(
            ExecutionSlice(
                interval=i,
                start_time=start,
                end_time=end,
                shares=max(0, shares),
                pct_of_order=round(shares / total_shares, 4),
            )
        )

    participation = (
        (shares_per_interval / interval_volume) if interval_volume > 0 else 0.0
    )

    return ExecutionSchedule(
        ticker=ticker.upper(),
        total_shares=total_shares,
        n_intervals=n_intervals,
        algorithm="TWAP",
        slices=slices,
        expected_completion=times[-1][1],
        participation_rate=round(participation, 4),
    )


def vwap_schedule(
    ticker: str,
    total_shares: int,
    n_intervals: int = 13,
    avg_daily_volume: int = 50_000_000,
    volume_profile: np.ndarray | None = None,
) -> ExecutionSchedule:
    """
    VWAP — Volume-Weighted Average Price execution schedule.

    Distributes shares proportional to expected intraday volume.
    More shares at open and close (high volume), fewer at midday.

    When to use:
      - You want to minimise market impact vs the VWAP benchmark
      - Suitable for medium-sized orders (1-5% of daily volume)
      - Standard benchmark for institutional execution desks

    Args:
        volume_profile:     custom volume weights (must sum to 1.0).
                            Defaults to U-shaped intraday profile.
    """
    if volume_profile is None:
        profile = default_volume_profile(n_intervals)
    else:
        profile = np.array(volume_profile, dtype=np.float64)
        profile = profile / profile.sum()  # normalise

    times = _interval_times(n_intervals)
    target_shares = (profile * total_shares).round().astype(int)

    # Fix rounding — ensure total matches exactly
    diff = total_shares - int(target_shares.sum())
    target_shares[np.argmax(profile)] += diff

    slices = []
    for i, (start, end) in enumerate(times):
        slices.append(
            ExecutionSlice(
                interval=i,
                start_time=start,
                end_time=end,
                shares=int(target_shares[i]),
                pct_of_order=round(float(target_shares[i]) / total_shares, 4),
            )
        )

    avg_participation = (
        float(total_shares / avg_daily_volume) if avg_daily_volume > 0 else 0.0
    )

    return ExecutionSchedule(
        ticker=ticker.upper(),
        total_shares=total_shares,
        n_intervals=n_intervals,
        algorithm="VWAP",
        slices=slices,
        expected_completion=times[-1][1],
        participation_rate=round(avg_participation, 4),
    )


def implementation_shortfall_schedule(
    ticker: str,
    total_shares: int,
    n_intervals: int = 13,
    urgency: float = 0.5,
    avg_daily_volume: int = 50_000_000,
) -> ExecutionSchedule:
    """
    Implementation Shortfall (IS) execution schedule.

    Front-loads the order when urgency is high (trade fast, accept
    more market impact), back-loads when urgency is low (trade slowly,
    minimise impact but accept more timing risk).

    IS minimises E[cost] = market_impact + timing_risk
    This tradeoff is parameterised by urgency.

    When to use:
      - Large orders where timing risk is significant
      - When you have a strong alpha signal (high urgency = capture it fast)
      - Sophisticated institutional execution

    Args:
        urgency:    0.0 = back-loaded (minimise impact, accept timing risk)
                    0.5 = balanced
                    1.0 = front-loaded (minimise timing risk, accept impact)
    """
    urgency = float(np.clip(urgency, 0.0, 1.0))

    # Exponential decay: higher urgency = steeper front-loading
    # decay_rate: urgency=0 → flat; urgency=1 → very steep
    decay_rate = urgency * 3.0  # scale factor
    t = np.arange(n_intervals, dtype=np.float64)
    weights = np.exp(-decay_rate * t / n_intervals)
    weights = weights / weights.sum()

    times = _interval_times(n_intervals)
    raw_shares = weights * total_shares
    target_shares = np.floor(raw_shares).astype(int)
    remainder = total_shares - int(target_shares.sum())
    if remainder > 0:
        fractional_order = np.argsort(raw_shares - target_shares)[::-1]
        target_shares[fractional_order[:remainder]] += 1

    slices = []
    for i, (start, end) in enumerate(times):
        slices.append(
            ExecutionSlice(
                interval=i,
                start_time=start,
                end_time=end,
                shares=int(target_shares[i]),
                pct_of_order=round(float(target_shares[i]) / total_shares, 4),
            )
        )

    avg_participation = (
        float(total_shares / avg_daily_volume) if avg_daily_volume > 0 else 0.0
    )
    urgency_label = (
        "aggressive (front-loaded)"
        if urgency > 0.66
        else "passive (back-loaded)"
        if urgency < 0.33
        else "balanced"
    )

    return ExecutionSchedule(
        ticker=ticker.upper(),
        total_shares=total_shares,
        n_intervals=n_intervals,
        algorithm=f"IS (urgency={urgency:.2f}, {urgency_label})",
        slices=slices,
        expected_completion=times[-1][1],
        participation_rate=round(avg_participation, 4),
    )


def analyse_execution(
    schedule: ExecutionSchedule,
    decision_price: float,
    execution_prices: list[float],
    market_prices: list[float],
) -> ExecutionAnalysis:
    """
    Post-trade execution quality analysis.

    Compares actual execution prices against benchmarks.

    Args:
        schedule:           the schedule that was used
        decision_price:     price when you decided to trade (alpha price)
        execution_prices:   actual prices you paid per interval
        market_prices:      market midpoint prices per interval (for VWAP)
    """
    shares = [s.shares for s in schedule.slices]
    total = sum(shares)

    if len(execution_prices) != len(shares):
        raise ValueError("execution_prices must match number of schedule slices")

    # Weighted average execution price
    weighted_cost = sum(p * s for p, s in zip(execution_prices, shares, strict=False))
    avg_exec_price = weighted_cost / total if total > 0 else 0.0

    # VWAP benchmark
    weighted_market = (
        sum(p * s for p, s in zip(market_prices, shares, strict=False))
        if market_prices
        else avg_exec_price
    )
    vwap_bench = weighted_market / total if total > 0 else avg_exec_price

    # Implementation shortfall in basis points (1 bps = 0.01%)
    # IS = (avg_exec - decision) / decision × 10000
    is_bps = (
        ((avg_exec_price - decision_price) / decision_price * 10_000)
        if decision_price > 0
        else 0.0
    )

    # Market impact vs VWAP
    impact_bps = (
        ((avg_exec_price - vwap_bench) / vwap_bench * 10_000) if vwap_bench > 0 else 0.0
    )

    participation = schedule.participation_rate

    if is_bps < 5:
        interp = f"Excellent execution. IS of {is_bps:.1f} bps is well within typical 10-20 bps range."
    elif is_bps < 20:
        interp = f"Good execution. IS of {is_bps:.1f} bps is within normal range."
    else:
        interp = f"High implementation shortfall of {is_bps:.1f} bps — consider lower urgency or smaller order size."

    return ExecutionAnalysis(
        algorithm=schedule.algorithm,
        total_shares=total,
        avg_execution_price=round(avg_exec_price, 4),
        vwap_benchmark=round(vwap_bench, 4),
        implementation_shortfall_bps=round(is_bps, 2),
        market_impact_bps=round(impact_bps, 2),
        participation_rate=participation,
        interpretation=interp,
    )
