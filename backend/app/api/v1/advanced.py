"""
AEQUITAS — Advanced algorithms API endpoints.

POST /api/v1/factor-model/{ticker}     Fama-French 3-factor analysis
POST /api/v1/execution/{ticker}/twap   TWAP execution schedule
POST /api/v1/execution/{ticker}/vwap   VWAP execution schedule
POST /api/v1/execution/{ticker}/is     Implementation Shortfall schedule
"""

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.execution.twap_vwap import (
    implementation_shortfall_schedule,
    twap_schedule,
    vwap_schedule,
)
from app.algorithms.signals.factor_model import run_factor_model
from app.db import get_db
from app.models.market_data import OHLCVBar

router = APIRouter()


class FactorModelResponse(BaseModel):
    ticker: str
    alpha: float
    alpha_pct: float
    alpha_tstat: float
    alpha_significant: bool
    beta_market: float
    beta_smb: float
    beta_hml: float
    r_squared: float
    residual_vol: float
    interpretation: str


class ExecutionSliceOut(BaseModel):
    interval: int
    start_time: str
    end_time: str
    shares: int
    pct_of_order: float


class ExecutionScheduleResponse(BaseModel):
    ticker: str
    total_shares: int
    n_intervals: int
    algorithm: str
    slices: list[ExecutionSliceOut]
    expected_completion: str
    participation_rate: float


class ExecutionRequest(BaseModel):
    total_shares: int = 10_000
    n_intervals: int = 13
    avg_daily_volume: int = 50_000_000
    urgency: float = 0.5


async def _get_log_returns(
    db: AsyncSession,
    ticker: str,
    min_rows: int = 60,
) -> pd.Series:
    result = await db.execute(
        select(OHLCVBar.time, OHLCVBar.close)
        .where(OHLCVBar.ticker == ticker.upper(), OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()
    if len(rows) < min_rows:
        raise HTTPException(
            status_code=404,
            detail=f"Need {min_rows}+ bars for {ticker}. Ingest data first.",
        )
    closes = pd.Series(
        [float(r.close) for r in rows],
        index=pd.DatetimeIndex([r.time for r in rows]),
    )
    ratio = closes / closes.shift(1)
    return ratio.apply(np.log).dropna()


@router.post("/api/v1/factor-model/{ticker}", response_model=FactorModelResponse)
async def factor_model(
    ticker: str,
    benchmark_a: str = "SPY",
    benchmark_b: str = "IWM",
    benchmark_c: str = "IVE",
    benchmark_d: str = "IWF",
    db: AsyncSession = Depends(get_db),
) -> FactorModelResponse:
    """
    Run Fama-French 3-factor model decomposition.
    Requires SPY, IWM, IVE, IWF to be ingested first.
    """
    try:
        stock_ret = await _get_log_returns(db, ticker, 60)
        market_ret = await _get_log_returns(db, benchmark_a, 60)
        small_ret = await _get_log_returns(db, benchmark_b, 60)
        value_ret = await _get_log_returns(db, benchmark_c, 60)
        growth_ret = await _get_log_returns(db, benchmark_d, 60)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        result = run_factor_model(
            stock_ret,
            market_ret,
            small_ret,
            value_ret,
            growth_ret,
            ticker=ticker.upper(),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return FactorModelResponse(
        ticker=result.ticker,
        alpha=result.alpha,
        alpha_pct=round(result.alpha * 100, 4),
        alpha_tstat=result.alpha_tstat,
        alpha_significant=abs(result.alpha_tstat) > 2.0,
        beta_market=result.beta_market,
        beta_smb=result.beta_smb,
        beta_hml=result.beta_hml,
        r_squared=result.r_squared,
        residual_vol=result.residual_vol,
        interpretation=result.interpretation,
    )


@router.post(
    "/api/v1/execution/{ticker}/twap", response_model=ExecutionScheduleResponse
)
async def twap_endpoint(
    ticker: str, req: ExecutionRequest
) -> ExecutionScheduleResponse:
    """TWAP — equal shares per time interval."""
    s = twap_schedule(
        ticker.upper(), req.total_shares, req.n_intervals, req.avg_daily_volume
    )
    return ExecutionScheduleResponse(
        ticker=s.ticker,
        total_shares=s.total_shares,
        n_intervals=s.n_intervals,
        algorithm=s.algorithm,
        slices=[ExecutionSliceOut(**sl.__dict__) for sl in s.slices],
        expected_completion=s.expected_completion,
        participation_rate=s.participation_rate,
    )


@router.post(
    "/api/v1/execution/{ticker}/vwap", response_model=ExecutionScheduleResponse
)
async def vwap_endpoint(
    ticker: str, req: ExecutionRequest
) -> ExecutionScheduleResponse:
    """VWAP — shares proportional to U-shaped intraday volume profile."""
    s = vwap_schedule(
        ticker.upper(), req.total_shares, req.n_intervals, req.avg_daily_volume
    )
    return ExecutionScheduleResponse(
        ticker=s.ticker,
        total_shares=s.total_shares,
        n_intervals=s.n_intervals,
        algorithm=s.algorithm,
        slices=[ExecutionSliceOut(**sl.__dict__) for sl in s.slices],
        expected_completion=s.expected_completion,
        participation_rate=s.participation_rate,
    )


@router.post("/api/v1/execution/{ticker}/is", response_model=ExecutionScheduleResponse)
async def is_endpoint(ticker: str, req: ExecutionRequest) -> ExecutionScheduleResponse:
    """Implementation Shortfall — urgency-parameterised front/back loading."""
    s = implementation_shortfall_schedule(
        ticker.upper(),
        req.total_shares,
        req.n_intervals,
        req.urgency,
        req.avg_daily_volume,
    )
    return ExecutionScheduleResponse(
        ticker=s.ticker,
        total_shares=s.total_shares,
        n_intervals=s.n_intervals,
        algorithm=s.algorithm,
        slices=[ExecutionSliceOut(**sl.__dict__) for sl in s.slices],
        expected_completion=s.expected_completion,
        participation_rate=s.participation_rate,
    )
