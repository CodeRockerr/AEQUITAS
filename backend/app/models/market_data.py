"""
AEQUITAS — Market data ORM models.

Concepts:
  - ORM (Object Relational Mapper): lets you work with database
    rows as Python objects instead of writing raw SQL.
    SQLAlchemy maps Python classes → Postgres tables.

  - Hypertable: a TimescaleDB concept. You create a normal table,
    then call create_hypertable() to make it time-partitioned.
    Queries that filter by time become dramatically faster.

  - OHLCV: Open, High, Low, Close, Volume — the standard format
    for financial time-series data. Every candlestick chart you've
    ever seen is built from OHLCV data.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OHLCVBar(Base):
    """
    One OHLCV bar (candlestick) for a ticker at a given timestamp.

    Table structure:
      - time:       the bar's timestamp (partition key for TimescaleDB)
      - ticker:     stock symbol e.g. "AAPL", "SPY"
      - open/high/low/close: prices as Decimal (never use float for money)
      - volume:     number of shares traded
      - interval:   "1d" daily, "1h" hourly, "5m" 5-minute, etc.

    Why Decimal not float?
      Float arithmetic is imprecise: 0.1 + 0.2 = 0.30000000000000004
      For financial data this causes errors in P&L calculations.
      Decimal is exact. Always use Decimal for prices.
    """

    __tablename__ = "ohlcv_bars"

    # TimescaleDB requires the time column to be part of the primary key
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False)
    interval: Mapped[str] = mapped_column(
        String(10), primary_key=True, nullable=False, default="1d"
    )

    # OHLCV — precision=12, scale=6 handles prices from $0.0001 to $999999
    open: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Composite index: makes queries like
    # "get all AAPL bars between date A and date B" fast
    __table_args__ = (
        Index("ix_ohlcv_ticker_time", "ticker", "time"),
        {"comment": "TimescaleDB hypertable — partitioned by time column"},
    )

    def __repr__(self) -> str:
        return f"OHLCVBar(ticker={self.ticker!r}, time={self.time}, close={self.close})"


class CompanyInfo(Base):
    """
    Static company metadata — updated infrequently.
    Separate table from OHLCV to avoid repeating strings millions of times.
    """

    __tablename__ = "company_info"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (UniqueConstraint("ticker", name="uq_company_ticker"),)

    def __repr__(self) -> str:
        return f"CompanyInfo(ticker={self.ticker!r}, name={self.name!r})"
