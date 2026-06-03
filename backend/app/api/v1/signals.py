"""
AEQUITAS — Signals and backtesting API endpoints.

GET  /api/v1/signals/{ticker}              momentum signals
POST /api/v1/signals/pairs                 pairs trading signal
POST /api/v1/backtest/{ticker}/{strategy}  run backtest
"""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.signals.momentum import combined_signal
from app.algorithms.signals.pairs import check_cointegration, pairs_signal
from app.backtesting.engine import (
    run_bollinger_backtest,
    run_macd_backtest,
    run_momentum_backtest,
)
from app.db import get_db
from app.models.market_data import OHLCVBar

router = APIRouter()


# ── Response schemas ──────────────────────────────────────────


class SignalResponse(BaseModel):
    ticker: str
    combined_signal: float
    direction: str
    signals: dict


class CointegrationResponse(BaseModel):
    ticker_a: str
    ticker_b: str
    is_cointegrated: bool
    p_value: float
    hedge_ratio: float
    half_life: float
    interpretation: str


class PairsSignalResponse(BaseModel):
    ticker_a: str
    ticker_b: str
    spread_zscore: float
    signal: float
    action: str
    hedge_ratio: float


class BacktestResponse(BaseModel):
    ticker: str
    strategy: str
    total_return_pct: float
    annual_return_pct: float
    annual_volatility_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate_pct: float
    n_trades: int
    avg_trade_duration_days: float
    benchmark_return_pct: float
    alpha_pct: float
    start_date: str
    end_date: str
    n_bars: int
    summary: str


class PairsTestRequest(BaseModel):
    ticker_a: str
    ticker_b: str


class PairsSignalRequest(BaseModel):
    ticker_a: str
    ticker_b: str
    entry_zscore: float = 2.0
    exit_zscore: float = 0.5
    use_kalman: bool = True


# ── Helper ────────────────────────────────────────────────────


async def _get_close_series(
    db: AsyncSession,
    ticker: str,
    min_rows: int = 60,
) -> pd.Series:
    result = await db.execute(
        select(OHLCVBar.time, OHLCVBar.close)
        .where(
            OHLCVBar.ticker == ticker.upper(),
            OHLCVBar.interval == "1d",
        )
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()

    if len(rows) < min_rows:
        raise HTTPException(
            status_code=404,
            detail=f"Need {min_rows}+ bars for {ticker}. "
            f"Call POST /api/v1/market-data/{ticker}/ingest first.",
        )

    times = [r.time for r in rows]
    closes = [float(r.close) for r in rows]
    return pd.Series(closes, index=pd.DatetimeIndex(times), name=ticker.upper())


# ── Endpoints ─────────────────────────────────────────────────


@router.get("/api/v1/signals/{ticker}", response_model=SignalResponse)
async def get_signals(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    """
    Get combined momentum signal for a ticker.

    Combines RSI, MACD, and Bollinger Band signals into one score.
    Score range: [-1, +1] where +1 = strong buy, -1 = strong sell.
    """
    close = await _get_close_series(db, ticker)

    result = combined_signal(close)

    return SignalResponse(
        ticker=ticker.upper(),
        combined_signal=result["combined_signal"],
        direction=result["direction"],
        signals=result["signals"],
    )


@router.post("/api/v1/signals/pairs/test", response_model=CointegrationResponse)
async def test_pair_cointegration(
    req: PairsTestRequest,
    db: AsyncSession = Depends(get_db),
) -> CointegrationResponse:
    """
    Test whether two tickers are cointegrated.

    Run this before generating pairs signals to confirm
    the pair is statistically tradeable.
    """
    close_a = await _get_close_series(db, req.ticker_a, min_rows=100)
    close_b = await _get_close_series(db, req.ticker_b, min_rows=100)

    result = check_cointegration(
        close_a,
        close_b,
        ticker_a=req.ticker_a.upper(),
        ticker_b=req.ticker_b.upper(),
    )

    return CointegrationResponse(
        ticker_a=result.ticker_a,
        ticker_b=result.ticker_b,
        is_cointegrated=result.is_cointegrated,
        p_value=result.p_value,
        hedge_ratio=result.hedge_ratio,
        half_life=result.half_life,
        interpretation=result.interpretation,
    )


@router.post("/api/v1/signals/pairs/signal", response_model=PairsSignalResponse)
async def get_pairs_signal(
    req: PairsSignalRequest,
    db: AsyncSession = Depends(get_db),
) -> PairsSignalResponse:
    """
    Get current pairs trading signal with Kalman filter hedge ratio.
    """
    close_a = await _get_close_series(db, req.ticker_a, min_rows=100)
    close_b = await _get_close_series(db, req.ticker_b, min_rows=100)

    result = pairs_signal(
        close_a,
        close_b,
        ticker_a=req.ticker_a.upper(),
        ticker_b=req.ticker_b.upper(),
        entry_zscore=req.entry_zscore,
        exit_zscore=req.exit_zscore,
        use_kalman=req.use_kalman,
    )

    return PairsSignalResponse(
        ticker_a=result.ticker_a,
        ticker_b=result.ticker_b,
        spread_zscore=result.spread_zscore,
        signal=result.signal,
        action=result.action,
        hedge_ratio=result.hedge_ratio,
    )


@router.post("/api/v1/backtest/{ticker}/{strategy}", response_model=BacktestResponse)
async def run_backtest(
    ticker: str,
    strategy: str,
    db: AsyncSession = Depends(get_db),
) -> BacktestResponse:
    """
    Run a backtest for a given ticker and strategy.

    Supported strategies: rsi, macd, bollinger

    Returns a full tearsheet with risk-adjusted performance metrics
    compared against buy-and-hold benchmark.
    """
    valid_strategies = ["rsi", "macd", "bollinger"]
    if strategy not in valid_strategies:
        raise HTTPException(
            status_code=422,
            detail=f"Strategy must be one of: {valid_strategies}",
        )

    close = await _get_close_series(db, ticker, min_rows=100)

    try:
        if strategy == "rsi":
            result = run_momentum_backtest(close, ticker.upper())
        elif strategy == "macd":
            result = run_macd_backtest(close, ticker.upper())
        else:
            result = run_bollinger_backtest(close, ticker.upper())
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Backtest failed: {e}",
        ) from e

    # Build human-readable summary
    alpha_sign = "+" if result.alpha_pct >= 0 else ""
    summary = (
        f"{result.strategy} on {result.ticker}: "
        f"{result.total_return_pct:+.1f}% total return "
        f"(vs {result.benchmark_return_pct:+.1f}% buy-and-hold, "
        f"alpha {alpha_sign}{result.alpha_pct:.1f}%). "
        f"Sharpe {result.sharpe_ratio:.2f}, "
        f"max drawdown {result.max_drawdown_pct:.1f}%, "
        f"{result.n_trades} trades at {result.win_rate_pct:.0f}% win rate."
    )

    return BacktestResponse(
        **result.__dict__,
        summary=summary,
    )
