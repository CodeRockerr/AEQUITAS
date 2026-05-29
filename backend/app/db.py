"""
AEQUITAS — Async database session management.

Concepts:
  - Connection pool: instead of opening/closing a DB connection
    on every request (slow), we keep a pool of open connections
    and reuse them. SQLAlchemy manages this automatically.

  - async session: we use async SQLAlchemy so database queries
    don't block the event loop. FastAPI can serve other requests
    while waiting for a DB query to complete.

  - Dependency injection: FastAPI's `Depends(get_db)` pattern
    gives each request its own session, commits on success,
    rolls back on error, and closes cleanly — automatically.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── Engine ────────────────────────────────────────────────────
# The engine manages the connection pool.
# echo=True logs all SQL in development — helpful for debugging,
# never use in production (too noisy, leaks query details).
engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.is_development,
    future=True,
)

# ── Session factory ───────────────────────────────────────────
# AsyncSessionLocal creates new session instances.
# expire_on_commit=False means we can still read attributes
# after committing (important for returning data in responses).
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base class for all ORM models ─────────────────────────────
class Base(DeclarativeBase):
    """
    All SQLAlchemy models inherit from this.
    It provides the metadata registry that Alembic
    uses to detect schema changes and generate migrations.
    """

    pass


# ── FastAPI dependency ────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in a route:
        from app.db import get_db
        from fastapi import Depends

        @router.get("/something")
        async def my_route(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(MyModel))

    The `async with` block ensures:
      - Session is created fresh for this request
      - Changes are committed if no exception
      - Session is closed when the request ends (even on error)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
