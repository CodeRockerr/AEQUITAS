"""
AEQUITAS — WebSocket endpoint for real-time price streaming.

Protocol:
  Client connects to /ws/prices
  Client sends: {"action": "subscribe", "ticker": "AAPL"}
  Client sends: {"action": "unsubscribe", "ticker": "AAPL"}
  Server sends: {"type": "price_update", "ticker": "AAPL", "price": 211.5, "change_pct": 1.2, "is_live": true, "timestamp": ...}
                 (is_live=false means market is closed — price is the last known daily close, not a live tick)
  Server sends: {"type": "subscribed", "ticker": "AAPL"}
  Server sends: {"type": "error", "message": "..."}

One WebSocket connection can subscribe to multiple tickers
simultaneously — the frontend opens one connection and sends
multiple subscribe messages.
"""

import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.price_stream import price_stream_manager

log = structlog.get_logger()
router = APIRouter()


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket) -> None:
    """
    Real-time price streaming WebSocket.

    Supports multiple ticker subscriptions per connection.
    Automatically cleans up subscriptions on disconnect.
    """
    await websocket.accept()
    subscribed_tickers: set[str] = set()

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                    }
                )
                continue

            action = message.get("action")
            ticker = message.get("ticker", "").upper().strip()

            if not ticker:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Missing 'ticker' field",
                    }
                )
                continue

            if action == "subscribe":
                await price_stream_manager.subscribe(ticker, websocket)
                subscribed_tickers.add(ticker)
                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "ticker": ticker,
                    }
                )
                log.info("ws_client_subscribed", ticker=ticker)

            elif action == "unsubscribe":
                await price_stream_manager.unsubscribe(ticker, websocket)
                subscribed_tickers.discard(ticker)
                await websocket.send_json(
                    {
                        "type": "unsubscribed",
                        "ticker": ticker,
                    }
                )

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    }
                )

    except WebSocketDisconnect:
        log.info("ws_client_disconnected", tickers=list(subscribed_tickers))
    finally:
        await price_stream_manager.unsubscribe_all(websocket)


@router.get("/api/v1/ws/status")
async def websocket_status() -> dict:
    """
    Debug endpoint — shows which tickers currently have active
    real-time refresh loops running.
    """
    active = price_stream_manager.active_tickers()
    return {
        "active_tickers": active,
        "count": len(active),
    }
