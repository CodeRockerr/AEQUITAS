"""
AEQUITAS — Full price history endpoint.

GET /api/v1/history/{ticker}?range=1mo|6mo|1y|5y|max

Returns complete OHLCV history for charting. Auto-ingests if the
ticker has never been seen before, or if existing history doesn't
go back far enough for the requested range (e.g. someone previously
ingested only 1y but now wants "max" / full history since listing).

This is the backbone of the Dashboard's price explorer — a person
can search any valid ticker and immediately see its full chart
history without ever calling POST /ingest manually.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import structlog
import yfinance as yf  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.market_data import OHLCVBar

log = structlog.get_logger()
router = APIRouter()

VALID_RANGES = {"1mo", "6mo", "1y", "5y", "max"}


class CandleOut(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoryResponse(BaseModel):
    ticker: str
    range: str
    candles: list[CandleOut]
    n_candles: int
    first_date: str | None
    last_date: str | None


async def _ingest_full_history(ticker: str) -> int:
    """
    Fetch and upsert the FULL price history for a ticker, from its
    first trading day to today. Uses yfinance's period="max".

    Returns number of new rows inserted.
    """
    from app.db import AsyncSessionLocal

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="max", interval="1d")
    except Exception as e:
        log.warning("full_history_fetch_failed", ticker=ticker, error=str(e))
        return 0

    if hist.empty:
        return 0

    timestamps: list[datetime] = [
        ts.to_pydatetime() for ts in pd.to_datetime(hist.index)
    ]

    rows_inserted = 0
    async with AsyncSessionLocal() as db:
        for bar_time, (_, row) in zip(timestamps, hist.iterrows(), strict=True):
            existing = await db.execute(
                select(OHLCVBar).where(
                    OHLCVBar.ticker == ticker,
                    OHLCVBar.time == bar_time,
                    OHLCVBar.interval == "1d",
                )
            )
            bar = existing.scalar_one_or_none()

            if bar is None:
                db.add(
                    OHLCVBar(
                        ticker=ticker,
                        time=bar_time,
                        interval="1d",
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                    )
                )
                rows_inserted += 1

        await db.commit()

    log.info("full_history_ingested", ticker=ticker, rows=rows_inserted)
    return rows_inserted


@router.get("/api/v1/history/{ticker}", response_model=HistoryResponse)
async def get_price_history(
    ticker: str,
    range_: str = Query(default="1y", description="1mo | 6mo | 1y | 5y | max"),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """
    Get full OHLCV price history for a ticker, for charting.

    If the ticker has never been ingested, or the requested range
    needs more history than currently stored, automatically fetches
    the complete history from yFinance (period=max) — covering every
    trading day since the stock's listing.

    range:
      1mo  — last ~21 trading days
      6mo  — last ~126 trading days
      1y   — last ~252 trading days
      5y   — last ~1260 trading days
      max  — entire available history (back to IPO/listing)
    """
    ticker = ticker.upper()

    if range_ not in VALID_RANGES:
        raise HTTPException(
            status_code=422,
            detail=f"range must be one of: {sorted(VALID_RANGES)}",
        )

    # Check what we already have
    earliest_result = await db.execute(
        select(OHLCVBar.time)
        .where(OHLCVBar.ticker == ticker, OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.asc())
        .limit(1)
    )
    earliest: datetime | None = earliest_result.scalar_one_or_none()

    # If we have no data at all, or this is the first time anyone asked
    # for "max" / "5y" range, do a full historical ingest.
    needs_full_ingest = earliest is None
    if earliest is not None and range_ in ("5y", "max"):
        earliest_aware = (
            earliest if earliest.tzinfo is not None else earliest.replace(tzinfo=UTC)
        )
        years_of_data = (datetime.now(UTC) - earliest_aware).days / 365
        if range_ == "max" and years_of_data < 4:
            # Heuristic: if we have less than 4 years and someone wants
            # "max", we probably only ever did a partial ingest before.
            needs_full_ingest = True
        elif range_ == "5y" and years_of_data < 4.5:
            needs_full_ingest = True

    if needs_full_ingest:
        rows = await _ingest_full_history(ticker)
        if rows == 0 and earliest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find any price data for '{ticker}'. "
                f"Check the ticker symbol is correct.",
            )

    # Determine the cutoff date for the requested range
    range_days = {
        "1mo": 31,
        "6mo": 183,
        "1y": 366,
        "5y": 1827,
        "max": None,
    }[range_]

    query = (
        select(OHLCVBar)
        .where(OHLCVBar.ticker == ticker, OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.asc())
    )

    bars_result = await db.execute(query)
    all_bars: list[OHLCVBar] = list(bars_result.scalars().all())

    if not all_bars:
        raise HTTPException(
            status_code=404,
            detail=f"No price data available for '{ticker}'.",
        )

    bars: list[OHLCVBar]
    if range_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=range_days)
        bars = [
            b
            for b in all_bars
            if (b.time if b.time.tzinfo is not None else b.time.replace(tzinfo=UTC))
            >= cutoff
        ]
    else:
        bars = all_bars

    candles = [
        CandleOut(
            time=b.time.isoformat(),
            open=float(b.open),
            high=float(b.high),
            low=float(b.low),
            close=float(b.close),
            volume=int(b.volume),
        )
        for b in bars
    ]

    return HistoryResponse(
        ticker=ticker,
        range=range_,
        candles=candles,
        n_candles=len(candles),
        first_date=candles[0].time if candles else None,
        last_date=candles[-1].time if candles else None,
    )
