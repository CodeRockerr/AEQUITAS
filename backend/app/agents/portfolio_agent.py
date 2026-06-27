"""
AEQUITAS — Portfolio construction agent.

Given a list of tickers, this agent:
  1. Runs cointegration tests on all pairs (flags tradeable pairs)
  2. Runs mean-variance optimisation to find max-Sharpe and
     min-variance weights
  3. Asks the LLM to synthesise a portfolio-level thesis explaining
     the allocation rationale, diversification quality, and risks

This reuses your existing portfolio optimiser and pairs trading
algorithms — the agent's job is orchestration and narrative, not
reimplementing math that already exists and is already tested.
"""

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.portfolio.optimiser import maximum_sharpe, minimum_variance
from app.algorithms.signals.pairs import check_cointegration
from app.models.market_data import OHLCVBar

log = structlog.get_logger()

MIN_ROWS_REQUIRED = 60


@dataclass
class PairCointegrationSummary:
    ticker_a: str
    ticker_b: str
    is_cointegrated: bool
    p_value: float
    half_life: float


@dataclass
class PortfolioAllocation:
    ticker: str
    max_sharpe_weight: float
    min_variance_weight: float


@dataclass
class PortfolioConstructionResult:
    tickers: list[str]
    allocations: list[PortfolioAllocation]
    max_sharpe_return: float
    max_sharpe_vol: float
    max_sharpe_ratio: float
    min_variance_vol: float
    cointegrated_pairs: list[PairCointegrationSummary]
    thesis: str
    errors: list[str] = field(default_factory=list)


async def _get_close_series(db: AsyncSession, ticker: str) -> pd.Series | None:
    result = await db.execute(
        select(OHLCVBar.time, OHLCVBar.close)
        .where(OHLCVBar.ticker == ticker.upper(), OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()
    if len(rows) < MIN_ROWS_REQUIRED:
        return None

    closes = pd.Series(
        [float(r.close) for r in rows],
        index=pd.DatetimeIndex([r.time for r in rows]),
        name=ticker.upper(),
    )
    return closes


async def run_portfolio_agent(
    tickers: list[str],
    db: AsyncSession,
    llm_call,
) -> PortfolioConstructionResult:
    """
    Run the portfolio construction agent across a list of tickers.

    Args:
        tickers: list of stock symbols (2-10 recommended)
        db: AsyncSession for fetching price history
        llm_call: async function (system, user, max_tokens) -> str
    """
    tickers = [t.upper() for t in tickers]
    errors: list[str] = []

    # Fetch price series for every ticker; skip any with insufficient data
    price_series: dict[str, pd.Series] = {}
    for ticker in tickers:
        series = await _get_close_series(db, ticker)
        if series is None:
            errors.append(
                f"{ticker}: insufficient price history (need {MIN_ROWS_REQUIRED}+ rows)"
            )
        else:
            price_series[ticker] = series

    valid_tickers = list(price_series.keys())
    if len(valid_tickers) < 2:
        return PortfolioConstructionResult(
            tickers=tickers,
            allocations=[],
            max_sharpe_return=0.0,
            max_sharpe_vol=0.0,
            max_sharpe_ratio=0.0,
            min_variance_vol=0.0,
            cointegrated_pairs=[],
            thesis="Insufficient data to construct a portfolio — need at least 2 tickers with 60+ days of price history.",
            errors=errors,
        )

    # Align all series to common dates, build a raw returns matrix
    # (shape: [n_days, n_assets]) — this is what maximum_sharpe() and
    # minimum_variance() expect as input; they compute mean/cov internally.
    price_df = pd.DataFrame(price_series)[valid_tickers].dropna()
    returns_df = price_df.pct_change().dropna()
    returns_matrix = returns_df.to_numpy(dtype=np.float64)

    max_sharpe = None
    min_var = None
    try:
        max_sharpe = maximum_sharpe(returns_matrix, valid_tickers)
        min_var = minimum_variance(returns_matrix, valid_tickers)
    except Exception as e:
        errors.append(f"Portfolio optimisation failed: {e}")

    allocations = []
    if max_sharpe and min_var:
        # weights are returned as list[float] in the same order as
        # `tickers` was passed in (valid_tickers here) — zip, don't .get()
        max_sharpe_by_ticker = dict(zip(valid_tickers, max_sharpe.weights, strict=True))
        min_var_by_ticker = dict(zip(valid_tickers, min_var.weights, strict=True))

        for ticker in valid_tickers:
            allocations.append(
                PortfolioAllocation(
                    ticker=ticker,
                    max_sharpe_weight=round(max_sharpe_by_ticker[ticker], 4),
                    min_variance_weight=round(min_var_by_ticker[ticker], 4),
                )
            )

    # ── Cointegration across all pairs ──────────────────────────
    cointegrated_pairs: list[PairCointegrationSummary] = []
    for ticker_a, ticker_b in combinations(valid_tickers, 2):
        try:
            result = check_cointegration(
                price_series[ticker_a],
                price_series[ticker_b],
                ticker_a=ticker_a,
                ticker_b=ticker_b,
            )
            if result.is_cointegrated:
                cointegrated_pairs.append(
                    PairCointegrationSummary(
                        ticker_a=ticker_a,
                        ticker_b=ticker_b,
                        is_cointegrated=True,
                        p_value=result.p_value,
                        half_life=result.half_life,
                    )
                )
        except Exception as e:
            log.warning(
                "portfolio_agent_cointegration_failed",
                pair=f"{ticker_a}/{ticker_b}",
                error=str(e),
            )

    # ── LLM synthesis ────────────────────────────────────────────
    allocation_summary = (
        "\n".join(
            f"- {a.ticker}: Max-Sharpe {a.max_sharpe_weight:.1%}, Min-Variance {a.min_variance_weight:.1%}"
            for a in allocations
        )
        if allocations
        else "Optimisation unavailable."
    )

    pairs_summary = (
        "\n".join(
            f"- {p.ticker_a}/{p.ticker_b}: cointegrated (p={p.p_value:.4f}, half-life={p.half_life:.1f} days)"
            for p in cointegrated_pairs
        )
        if cointegrated_pairs
        else "No statistically significant cointegrated pairs found."
    )

    max_sharpe_ret = max_sharpe.expected_return if max_sharpe else 0.0
    max_sharpe_vol = max_sharpe.volatility if max_sharpe else 0.0
    max_sharpe_ratio = max_sharpe.sharpe_ratio if max_sharpe else 0.0
    min_var_vol = min_var.volatility if min_var else 0.0

    thesis = await llm_call(
        system=(
            "You are a portfolio construction specialist. Given optimised allocations "
            "and pairs-trading opportunities across a set of tickers, write a portfolio "
            "thesis covering: allocation rationale, diversification quality, any "
            "cointegrated pairs worth a pairs-trade overlay, and key risks. "
            "Be specific and reference the actual numbers given."
        ),
        user=(
            f"Tickers: {', '.join(valid_tickers)}\n\n"
            f"=== MEAN-VARIANCE ALLOCATIONS ===\n{allocation_summary}\n\n"
            f"Max-Sharpe Portfolio: {max_sharpe_ret:.1%} expected return, "
            f"{max_sharpe_vol:.1%} volatility, Sharpe {max_sharpe_ratio:.2f}\n"
            f"Min-Variance Portfolio: {min_var_vol:.1%} volatility\n\n"
            f"=== COINTEGRATED PAIRS ===\n{pairs_summary}\n\n"
            "Write a 300-400 word portfolio construction thesis."
        ),
        max_tokens=700,
    )

    return PortfolioConstructionResult(
        tickers=tickers,
        allocations=allocations,
        max_sharpe_return=round(max_sharpe_ret, 4),
        max_sharpe_vol=round(max_sharpe_vol, 4),
        max_sharpe_ratio=round(max_sharpe_ratio, 4),
        min_variance_vol=round(min_var_vol, 4),
        cointegrated_pairs=cointegrated_pairs,
        thesis=thesis.strip(),
        errors=errors,
    )
