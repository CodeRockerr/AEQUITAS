"""
AEQUITAS — Market data API endpoints.

GET  /api/v1/market-data/{ticker}          fetch + store latest data
GET  /api/v1/market-data/{ticker}/bars     query stored OHLCV bars
GET  /api/v1/market-data/{ticker}/info     company metadata
"""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.ingestion.market_data import (
    fetch_and_store_company_info,
    fetch_and_store_ohlcv,
)
from app.db import get_db
from app.models.market_data import CompanyInfo, OHLCVBar

router = APIRouter(prefix="/api/v1/market-data")


# ── Response schemas ──────────────────────────────────────────


class OHLCVBarResponse(BaseModel):
    """What the API returns for each OHLCV bar."""

    time: datetime
    ticker: str
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    model_config = {"from_attributes": True}  # allows ORM → Pydantic conversion


class CompanyInfoResponse(BaseModel):
    ticker: str
    name: str
    sector: str | None
    industry: str | None
    description: str | None
    market_cap: int | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    ticker: str
    rows_ingested: int
    period: str
    interval: str


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/{ticker}/ingest", response_model=IngestResponse)
async def ingest_market_data(
    ticker: str,
    period: str = Query(default="1y", description="e.g. 1d, 5d, 1mo, 1y, 5y"),
    interval: str = Query(default="1d", description="e.g. 1m, 5m, 1h, 1d"),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """
    Fetch market data from Yahoo Finance and store in TimescaleDB.

    This is the entry point for loading data. Call this once per
    ticker before querying bars. It's idempotent — safe to call
    multiple times (uses upsert).
    """
    try:
        rows = await fetch_and_store_ohlcv(db, ticker, period, interval)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch data from Yahoo Finance: {e}",
        ) from e

    return IngestResponse(
        ticker=ticker.upper(),
        rows_ingested=rows,
        period=period,
        interval=interval,
    )


@router.get("/{ticker}/bars", response_model=list[OHLCVBarResponse])
async def get_ohlcv_bars(
    ticker: str,
    interval: str = Query(default="1d"),
    limit: int = Query(default=252, le=5000, description="Max bars to return"),
    db: AsyncSession = Depends(get_db),
) -> list[OHLCVBar]:
    """
    Query stored OHLCV bars for a ticker.

    Returns the most recent `limit` bars ordered oldest → newest.
    252 is the default (approx. trading days in a year).
    """
    result = await db.execute(
        select(OHLCVBar)
        .where(
            OHLCVBar.ticker == ticker.upper(),
            OHLCVBar.interval == interval,
        )
        .order_by(OHLCVBar.time.desc())
        .limit(limit)
    )
    bars = list(reversed(result.scalars().all()))

    if not bars:
        raise HTTPException(
            status_code=404,
            detail=f"No bars found for {ticker.upper()}. "
            f"Call POST /{ticker}/ingest first.",
        )

    return bars


@router.get("/{ticker}/info", response_model=CompanyInfoResponse)
async def get_company_info(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> CompanyInfo:
    """
    Get company metadata for a ticker.
    Fetches from Yahoo Finance if not already stored.
    """
    info = await db.get(CompanyInfo, ticker.upper())

    if info is None:
        try:
            info = await fetch_and_store_company_info(db, ticker)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    return info
