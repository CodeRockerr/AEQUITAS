"""
AEQUITAS — pgvector document store for RAG.

Uses PostgreSQL full-text search for retrieval.
pgvector is already enabled via init-db.sql.
"""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DocumentChunk(Base):
    """
    A chunk of a financial document stored for RAG retrieval.

    We use Mapped[] annotations (SQLAlchemy 2.0 style) instead of
    Column() with plain type hints — this satisfies both SQLAlchemy
    and Pylance simultaneously.
    """

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_chunk_hash"),
        Index("ix_chunks_ticker_source", "ticker", "source"),
    )


async def store_document_chunks(
    db: AsyncSession,
    ticker: str,
    source: str,
    chunks: list[str],
) -> int:
    """
    Store document chunks with deduplication via content hash.
    Returns number of chunks inserted (skips duplicates).
    """
    stored = 0
    now = datetime.now(UTC)

    for i, chunk in enumerate(chunks):
        content_hash = hashlib.sha256(f"{ticker}:{source}:{chunk}".encode()).hexdigest()

        await db.execute(
            sql_text("""
                INSERT INTO document_chunks
                    (ticker, source, chunk_index, content, content_hash, created_at)
                VALUES
                    (:ticker, :source, :chunk_index, :content, :hash, :created_at)
                ON CONFLICT (content_hash) DO NOTHING
            """),
            {
                "ticker": ticker.upper(),
                "source": source,
                "chunk_index": i,
                "content": chunk,
                "hash": content_hash,
                "created_at": now,
            },
        )
        stored += 1

    return stored


async def retrieve_relevant_chunks(
    db: AsyncSession,
    ticker: str,
    query: str,
    n_chunks: int = 5,
) -> list[dict]:
    """
    Retrieve most relevant chunks via PostgreSQL full-text search.
    """
    result = await db.execute(
        sql_text("""
            SELECT
                content,
                source,
                chunk_index,
                ts_rank(
                    to_tsvector('english', content),
                    plainto_tsquery('english', :query)
                ) AS relevance
            FROM document_chunks
            WHERE
                ticker = :ticker
                AND to_tsvector('english', content) @@
                    plainto_tsquery('english', :query)
            ORDER BY relevance DESC
            LIMIT :n_chunks
        """),
        {"ticker": ticker.upper(), "query": query, "n_chunks": n_chunks},
    )
    rows = result.fetchall()

    return [
        {
            "content": row.content,
            "source": row.source,
            "relevance": round(float(row.relevance), 4),
        }
        for row in rows
    ]


async def get_all_chunks_for_ticker(
    db: AsyncSession,
    ticker: str,
    limit: int = 20,
) -> list[dict]:
    """Fallback: return most recent chunks when no query matches."""
    result = await db.execute(
        sql_text("""
            SELECT content, source, chunk_index
            FROM document_chunks
            WHERE ticker = :ticker
            ORDER BY created_at DESC, chunk_index ASC
            LIMIT :limit
        """),
        {"ticker": ticker.upper(), "limit": limit},
    )
    rows = result.fetchall()
    return [
        {"content": row.content, "source": row.source, "relevance": 0.5} for row in rows
    ]


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """
    Split text into overlapping word-level chunks.

    overlap words from chunk N appear at the start of chunk N+1,
    ensuring context is never lost at boundaries.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap

    return chunks
