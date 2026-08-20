"""
AEQUITAS - Market data API endpoints.

GET  /api/v1/market-data/{ticker}          fetch + store latest data
GET  /api/v1/market-data/{ticker}/bars     query stored OHLCV bars
GET  /api/v1/market-data/{ticker}/info     company metadata
POST /api/v1/market-data/refresh-universe  bulk ingest/refresh the ticker universe
"""

from datetime import datetime
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.ingestion.market_data import (
    fetch_and_store_company_info,
    fetch_and_store_ohlcv,
)
from app.data.ingestion.universe import TICKER_UNIVERSE
from app.db import get_db
from app.models.market_data import CompanyInfo, OHLCVBar

log = structlog.get_logger()

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


class TickerRefreshResult(BaseModel):
    ticker: str
    rows_ingested: int | None
    error: str | None


class RefreshUniverseResponse(BaseModel):
    period: str
    interval: str
    results: list[TickerRefreshResult]
    succeeded: int
    failed: int


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
    ticker before querying bars. It's idempotent - safe to call
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


@router.post("/refresh-universe", response_model=RefreshUniverseResponse)
async def refresh_universe(
    period: str = Query(
        default="5d",
        description=(
            "yFinance period. Use the short default ('5d') for the routine "
            "scheduled top-up - upsert means overlapping days are harmless. "
            "Use 'max' for a one-time full historical backfill."
        ),
    ),
    interval: str = Query(default="1d"),
    db: AsyncSession = Depends(get_db),
) -> RefreshUniverseResponse:
    """
    Bulk ingest/refresh OHLCV data for every ticker in TICKER_UNIVERSE
    (the tickers the frontend's pickers and the factor model actually
    reference) in one call.

    Two use cases, one endpoint:
      - period=max (run once, manually): full historical backfill for
        every ticker in the universe, so charts/backtests/signals have
        complete history without waiting on each one's first user
        request to trigger the existing lazy auto-ingest individually.
      - period=5d (the scheduled default): "did new prices arrive?" -
        re-fetches just the last few trading days so today's close
        lands in the database. Cheap, and safe to run daily since
        fetch_and_store_ohlcv upserts (ON CONFLICT DO UPDATE).

    Keeps going past a single ticker's failure (delisted symbol,
    transient yFinance hiccup) rather than aborting the whole batch -
    each ticker gets its own commit/rollback.
    """
    results: list[TickerRefreshResult] = []

    for ticker in TICKER_UNIVERSE:
        try:
            rows = await fetch_and_store_ohlcv(db, ticker, period, interval)
            await db.commit()
            results.append(
                TickerRefreshResult(ticker=ticker, rows_ingested=rows, error=None)
            )
        except Exception as e:
            await db.rollback()
            log.warning("universe_refresh_ticker_failed", ticker=ticker, error=str(e))
            results.append(
                TickerRefreshResult(ticker=ticker, rows_ingested=None, error=str(e))
            )

    succeeded = sum(1 for r in results if r.error is None)
    return RefreshUniverseResponse(
        period=period,
        interval=interval,
        results=results,
        succeeded=succeeded,
        failed=len(results) - succeeded,
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
