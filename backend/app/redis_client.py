"""
AEQUITAS - Redis client, lazily created.

Mirrors db.py's pattern (one shared connection, created on first use) but
for Redis instead of Postgres. Currently used for one purpose: a global
counter of how many times the live benchmarks have been run (see
app/api/v1/benchmark.py's /benchmark/run-count).

Sync, not async: every benchmark endpoint that increments this counter is
a plain `def` (FastAPI runs those in a thread pool because the actual
work - numpy/pandas/C++ calls - is CPU-bound, not I/O-bound), so an async
Redis client would need `asyncio.run()` gymnastics for no benefit. A
single INCR is sub-millisecond; blocking briefly on it is fine here.

Degrades gracefully - if Redis is unreachable (misconfigured URL, network
blip), callers get None back instead of a 500. A benchmark page shouldn't
go down because a "fun fact" counter couldn't connect.
"""

import redis

from app.config import settings

_client: redis.Redis | None = None

RUN_COUNT_KEY = "aequitas:benchmark:run_count"


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def increment_run_count() -> None:
    """Best-effort - never let a counter failure break a benchmark endpoint."""
    try:
        get_redis().incr(RUN_COUNT_KEY)
    except Exception:
        pass


def get_run_count() -> int | None:
    try:
        value = get_redis().get(RUN_COUNT_KEY)
        return int(value) if value is not None else 0
    except Exception:
        return None
