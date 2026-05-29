"""
AEQUITAS — Pytest configuration and shared fixtures.

conftest.py is automatically loaded by Pytest before any tests run.
Fixtures defined here are available in ALL test files without importing.

Why no return type annotations on fixtures?
  Pytest fixtures use yield, making them generators internally.
  The correct annotation would be Generator[TestClient, None, None]
  which is verbose and adds no real value for fixture functions.
  Dropping the annotation is the standard convention for pytest fixtures.
"""

from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Return app settings for the test session.
    Clears lru_cache so tests don't share state with production config.
    """
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="session")
def app(test_settings: Settings):  # noqa: ANN201
    """
    Create a single FastAPI app instance for the whole test session.
    scope="session" = created once, reused across all test files.
    """
    return create_app()


@pytest.fixture(scope="session")
def client(app):  # noqa: ANN201
    """
    Synchronous test client.

    Use for straightforward endpoint tests — the vast majority.
    TestClient runs the ASGI app in-process, no server needed.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient]:
    """
    Async test client.

    Use when testing WebSocket endpoints or truly async behaviour.
    The return type AsyncGenerator[AsyncClient, None] correctly
    describes a function that yields an AsyncClient.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
