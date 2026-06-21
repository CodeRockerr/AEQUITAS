"""
AEQUITAS — Auto-ingest helper for the real-time feature.

Before this, a person had to manually POST /ingest before any
endpoint would return data for a ticker. This helper makes that
automatic — if a ticker has no data (or stale data), it's fetched
transparently on first request.

Use this inside any endpoint that needs guaranteed fresh data
for an arbitrary, possibly-never-seen ticker.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import structlog
import yfinance as yf  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import OHLCVBar

log = structlog.get_logger()

STALE_AFTER_HOURS = 20  # re-ingest if most recent bar is older than this


async def ensure_ticker_data(
    db: AsyncSession,
    ticker: str,
    period: str = "1y",
) -> int:
    """
    Ensure a ticker has reasonably fresh data in the database.

    If no data exists, or the most recent bar is stale (older than
    STALE_AFTER_HOURS), fetches fresh data from yFinance and upserts.

    Returns the number of rows in the database for this ticker
    after this call (0 if the ticker is invalid / fetch failed).

    This is what lets the frontend ask for "any ticker" without a
    person ever calling POST /ingest manually first.
    """
    ticker = ticker.upper()

    result = await db.execute(
        select(OHLCVBar.time)
        .where(OHLCVBar.ticker == ticker, OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.desc())
        .limit(1)
    )
    most_recent = result.scalar_one_or_none()

    needs_fetch = most_recent is None
    if most_recent is not None:
        age = datetime.now(UTC) - most_recent.replace(tzinfo=UTC)
        needs_fetch = age > timedelta(hours=STALE_AFTER_HOURS)

    if not needs_fetch:
        count_result = await db.execute(
            select(OHLCVBar.time).where(
                OHLCVBar.ticker == ticker, OHLCVBar.interval == "1d"
            )
        )
        return len(count_result.all())

    log.info("auto_ingest_triggered", ticker=ticker, reason="stale_or_missing")

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval="1d")
    except Exception as e:
        log.warning("auto_ingest_fetch_failed", ticker=ticker, error=str(e))
        return 0

    if hist.empty:
        log.warning("auto_ingest_empty_result", ticker=ticker)
        return 0

    rows_upserted = 0
    timestamps: list[datetime] = [
        ts.to_pydatetime() for ts in pd.to_datetime(hist.index)
    ]
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
            bar = OHLCVBar(
                ticker=ticker,
                time=bar_time,
                interval="1d",
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
            db.add(bar)
            rows_upserted += 1

    await db.commit()
    log.info("auto_ingest_complete", ticker=ticker, rows=rows_upserted)

    count_result = await db.execute(
        select(OHLCVBar.time).where(
            OHLCVBar.ticker == ticker, OHLCVBar.interval == "1d"
        )
    )
    return len(count_result.all())
