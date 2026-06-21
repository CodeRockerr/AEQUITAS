"""
AEQUITAS — Unit tests for the real-time price streaming service.

We test the subscriber-tracking logic directly, using a fake
WebSocket object, rather than spinning up a real WebSocket server.
This keeps tests fast and isolated from network/yfinance calls.
"""

from unittest.mock import AsyncMock

import pytest

from app.services.price_stream import PriceStreamManager


class FakeWebSocket:
    """Minimal stand-in for fastapi.WebSocket in unit tests."""

    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.send_json = AsyncMock(side_effect=self._record)

    async def _record(self, message: dict) -> None:
        self.sent_messages.append(message)


@pytest.fixture
def manager() -> PriceStreamManager:
    return PriceStreamManager()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_creates_subscription(manager: PriceStreamManager) -> None:
    ws = FakeWebSocket()
    await manager.subscribe("AAPL", ws)  # type: ignore[arg-type]
    assert "AAPL" in manager._subscriptions
    assert ws in manager._subscriptions["AAPL"].connections


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_normalises_ticker_case(manager: PriceStreamManager) -> None:
    ws = FakeWebSocket()
    await manager.subscribe("aapl", ws)  # type: ignore[arg-type]
    assert "AAPL" in manager._subscriptions
    assert "aapl" not in manager._subscriptions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_subscribers_same_ticker(manager: PriceStreamManager) -> None:
    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    await manager.subscribe("AAPL", ws1)  # type: ignore[arg-type]
    await manager.subscribe("AAPL", ws2)  # type: ignore[arg-type]
    assert len(manager._subscriptions["AAPL"].connections) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_removes_connection(manager: PriceStreamManager) -> None:
    ws = FakeWebSocket()
    await manager.subscribe("AAPL", ws)  # type: ignore[arg-type]
    await manager.unsubscribe("AAPL", ws)  # type: ignore[arg-type]
    assert ws not in manager._subscriptions["AAPL"].connections


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_nonexistent_ticker_no_error(
    manager: PriceStreamManager,
) -> None:
    ws = FakeWebSocket()
    # Should not raise even though ticker was never subscribed
    await manager.unsubscribe("NOPE", ws)  # type: ignore[arg-type]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unsubscribe_all_removes_from_every_ticker(
    manager: PriceStreamManager,
) -> None:
    ws = FakeWebSocket()
    await manager.subscribe("AAPL", ws)  # type: ignore[arg-type]
    await manager.subscribe("MSFT", ws)  # type: ignore[arg-type]
    await manager.unsubscribe_all(ws)  # type: ignore[arg-type]
    assert ws not in manager._subscriptions["AAPL"].connections
    assert ws not in manager._subscriptions["MSFT"].connections


@pytest.mark.unit
def test_active_tickers_excludes_empty_subscriptions(
    manager: PriceStreamManager,
) -> None:
    from app.services.price_stream import TickerSubscription

    manager._subscriptions["AAPL"] = TickerSubscription(
        ticker="AAPL",
        connections={object()},  # type: ignore[arg-type]
    )
    manager._subscriptions["MSFT"] = TickerSubscription(
        ticker="MSFT", connections=set()
    )

    active = manager.active_tickers()
    assert "AAPL" in active
    assert "MSFT" not in active


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_sends_to_all_connections(manager: PriceStreamManager) -> None:
    from app.services.price_stream import TickerSubscription

    ws1, ws2 = FakeWebSocket(), FakeWebSocket()
    sub = TickerSubscription(ticker="AAPL", connections={ws1, ws2})  # type: ignore[arg-type]

    await manager._broadcast(sub, price=211.5, change_pct=1.2, is_live=True)

    assert ws1.sent_messages[0]["ticker"] == "AAPL"
    assert ws1.sent_messages[0]["price"] == 211.5
    assert ws2.sent_messages[0]["price"] == 211.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections(manager: PriceStreamManager) -> None:
    from app.services.price_stream import TickerSubscription

    ws_dead = FakeWebSocket()
    ws_dead.send_json = AsyncMock(side_effect=ConnectionError("closed"))
    ws_alive = FakeWebSocket()

    sub = TickerSubscription(
        ticker="AAPL",
        connections={ws_dead, ws_alive},  # type: ignore[arg-type]
    )

    await manager._broadcast(sub, price=100.0, change_pct=0.5, is_live=True)

    assert ws_dead not in sub.connections
    assert ws_alive in sub.connections


@pytest.mark.unit
def test_fetch_price_sync_handles_invalid_ticker() -> None:
    """Invalid/delisted tickers should return None, not raise."""
    result = PriceStreamManager._fetch_price_sync("ZZZZZZINVALID")
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_with_fallback_uses_db_when_live_fails(
    manager: PriceStreamManager,
) -> None:
    """
    When the live yfinance fetch returns None (e.g. market closed),
    the manager should fall back to the database and mark is_live=False.
    """
    manager._fetch_price_live = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._fetch_price_from_db = AsyncMock(return_value=(190.5, -0.3))  # type: ignore[method-assign]

    result = await manager._fetch_price_with_fallback("AAPL")

    assert result == (190.5, -0.3, False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_with_fallback_prefers_live_when_available(
    manager: PriceStreamManager,
) -> None:
    """When live data is available, it should be used (is_live=True),
    and the DB fallback should never be queried."""
    manager._fetch_price_live = AsyncMock(return_value=(211.5, 1.2))  # type: ignore[method-assign]
    manager._fetch_price_from_db = AsyncMock(return_value=(190.5, -0.3))  # type: ignore[method-assign]

    result = await manager._fetch_price_with_fallback("AAPL")

    assert result == (211.5, 1.2, True)
    manager._fetch_price_from_db.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_with_fallback_returns_none_when_both_fail(
    manager: PriceStreamManager,
) -> None:
    """If neither live nor DB has any data, return None entirely."""
    manager._fetch_price_live = AsyncMock(return_value=None)  # type: ignore[method-assign]
    manager._fetch_price_from_db = AsyncMock(return_value=None)  # type: ignore[method-assign]

    result = await manager._fetch_price_with_fallback("ZZZZZ")

    assert result is None
