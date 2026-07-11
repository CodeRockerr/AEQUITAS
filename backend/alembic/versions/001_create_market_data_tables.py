"""create market data tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── company_info ──────────────────────────────────────────
    op.create_table(
        "company_info",
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("market_cap", sa.BigInteger, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── ohlcv_bars ────────────────────────────────────────────
    op.create_table(
        "ohlcv_bars",
        sa.Column("time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("ticker", sa.String(20), primary_key=True),
        sa.Column("interval", sa.String(10), primary_key=True),
        sa.Column("open", sa.Numeric(12, 6), nullable=False),
        sa.Column("high", sa.Numeric(12, 6), nullable=False),
        sa.Column("low", sa.Numeric(12, 6), nullable=False),
        sa.Column("close", sa.Numeric(12, 6), nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=False),
    )

    # ── Convert ohlcv_bars to a TimescaleDB hypertable, if available ──
    # On TimescaleDB-enabled infra (e.g. the timescale/timescaledb-ha
    # image) this partitions ohlcv_bars by 'time' in weekly chunks.
    # On plain Postgres (e.g. Neon) the extension is not available, so
    # this block is skipped and ohlcv_bars remains a regular table —
    # the (ticker, time) index below covers our query patterns either way.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_available_extensions
                WHERE name = 'timescaledb'
            ) THEN
                CREATE EXTENSION IF NOT EXISTS timescaledb;
                PERFORM create_hypertable(
                    'ohlcv_bars',
                    'time',
                    chunk_time_interval => INTERVAL '7 days',
                    if_not_exists => TRUE
                );
            END IF;
        END
        $$;
        """
    )

    # ── Indexes ───────────────────────────────────────────────
    op.create_index("ix_ohlcv_ticker_time", "ohlcv_bars", ["ticker", "time"])


def downgrade() -> None:
    op.drop_index("ix_ohlcv_ticker_time", "ohlcv_bars")
    op.drop_table("ohlcv_bars")
    op.drop_table("company_info")
