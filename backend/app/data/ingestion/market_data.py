"""
AEQUITAS — Market data ingestion via yFinance.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import structlog
import yfinance as yf
from pydantic import BaseModel, field_validator
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import CompanyInfo, OHLCVBar

log = structlog.get_logger()


# ── Pydantic schemas ──────────────────────────────────────────


class OHLCVRow(BaseModel):
    time: datetime
    ticker: str
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("open", "high", "low", "close")
    @classmethod
    def price_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError(f"Price must be positive, got {v}")
        return v

    @field_validator("volume")
    @classmethod
    def volume_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"Volume cannot be negative, got {v}")
        return v


class CompanyInfoRow(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    market_cap: int | None = None
    updated_at: datetime


# ── Timestamp normalisation ───────────────────────────────────


def _to_utc_datetime(ts: object) -> datetime:
    """
    Safely convert any timestamp type to a UTC-aware datetime.

    yFinance has changed its index type across versions:
      - Older versions: pandas Timestamp
      - Newer versions (>=0.2.50): datetime or other types

    This function handles all cases cleanly.
    """
    if isinstance(ts, pd.Timestamp):
        dt = ts.to_pydatetime()
    elif isinstance(ts, datetime):
        dt = ts
    else:
        # Fallback: try converting via pandas
        dt = pd.Timestamp(ts).to_pydatetime()  # type: ignore[arg-type]

    # Ensure UTC timezone awareness
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


# ── Ingestion functions ───────────────────────────────────────


async def fetch_and_store_ohlcv(
    db: AsyncSession,
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> int:
    """
    Fetch OHLCV data from yFinance and upsert into TimescaleDB.

    Returns number of rows upserted.
    Raises ValueError if ticker is invalid or no data returned.
    """
    ticker = ticker.upper().strip()
    log.info("ingestion_start", ticker=ticker, period=period, interval=interval)

    # ── 1. Fetch from Yahoo Finance ───────────────────────────
    yf_ticker = yf.Ticker(ticker)
    df = yf_ticker.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(
            f"No data returned for ticker '{ticker}'. "
            "Check the symbol is valid and the period/interval "
            "combination is supported by yFinance."
        )

    # ── 2. Validate and transform ─────────────────────────────
    rows: list[dict] = []
    skipped = 0

    for ts, row in df.iterrows():
        try:
            bar_time = _to_utc_datetime(ts)

            validated = OHLCVRow(
                time=bar_time,
                ticker=ticker,
                interval=interval,
                open=Decimal(str(round(float(row["Open"]), 6))),
                high=Decimal(str(round(float(row["High"]), 6))),
                low=Decimal(str(round(float(row["Low"]), 6))),
                close=Decimal(str(round(float(row["Close"]), 6))),
                volume=int(row["Volume"]),
            )
            rows.append(validated.model_dump())
        except Exception as e:
            log.warning(
                "row_validation_failed",
                ticker=ticker,
                ts=str(ts),
                error=str(e),
            )
            skipped += 1

    if not rows:
        raise ValueError(f"All rows failed validation for ticker '{ticker}'")

    # ── 3. Upsert into database ───────────────────────────────
    stmt = insert(OHLCVBar).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["time", "ticker", "interval"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
        },
    )
    await db.execute(stmt)

    log.info(
        "ingestion_complete",
        ticker=ticker,
        rows_upserted=len(rows),
        rows_skipped=skipped,
    )
    return len(rows)


async def fetch_and_store_company_info(
    db: AsyncSession,
    ticker: str,
) -> CompanyInfo:
    """Fetch company metadata from yFinance and upsert into DB."""
    ticker = ticker.upper().strip()
    yf_ticker = yf.Ticker(ticker)
    info = yf_ticker.info

    if not info or "shortName" not in info:
        raise ValueError(f"Could not fetch company info for '{ticker}'")

    validated = CompanyInfoRow(
        ticker=ticker,
        name=info.get("shortName", ticker),
        sector=info.get("sector"),
        industry=info.get("industry"),
        description=info.get("longBusinessSummary"),
        market_cap=info.get("marketCap"),
        updated_at=datetime.now(UTC),
    )

    stmt = insert(CompanyInfo).values(validated.model_dump())
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker"],
        set_={k: v for k, v in validated.model_dump().items() if k != "ticker"},
    )
    await db.execute(stmt)

    log.info("company_info_stored", ticker=ticker, name=validated.name)

    result = await db.get(CompanyInfo, ticker)
    return result  # type: ignore[return-value]
