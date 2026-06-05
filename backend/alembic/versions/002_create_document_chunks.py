"""create document chunks table for RAG

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_hash", name="uq_chunk_hash"),
    )
    op.create_index("ix_chunks_ticker", "document_chunks", ["ticker"])
    op.create_index(
        "ix_chunks_ticker_source",
        "document_chunks",
        ["ticker", "source"],
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_ticker_source", "document_chunks")
    op.drop_index("ix_chunks_ticker", "document_chunks")
    op.drop_table("document_chunks")
