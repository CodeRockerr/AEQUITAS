"""
AEQUITAS — Real-time price streaming service.

Architecture:
  - Tracks which tickers have active WebSocket subscribers
  - A background task refreshes ONLY actively-watched tickers,
    on a fixed interval (default 12s)
  - When a refresh produces a new price, it's broadcast to every
    WebSocket connection subscribed to that ticker

This subscriber-based throttling is what keeps us within yFinance's
unofficial rate limits even as the number of watched tickers grows —
we never poll a ticker nobody is currently viewing.

If a ticker has zero subscribers, its refresh loop stops automatically.
"""

import asyncio
import time
from dataclasses import dataclass, field

import structlog
import yfinance as yf  # type: ignore[import-untyped]
from fastapi import WebSocket

log = structlog.get_logger()

REFRESH_INTERVAL_SECONDS = 12.0
STALE_THRESHOLD_SECONDS = (
    60.0  # if a ticker has no subscribers for this long, fully drop it
)


@dataclass
class TickerSubscription:
    """Tracks WebSocket connections subscribed to one ticker."""

    ticker: str
    connections: set[WebSocket] = field(default_factory=set)
    last_price: float | None = None
    last_change_pct: float | None = None
    last_updated: float = field(default_factory=time.time)
    refresh_task: asyncio.Task | None = None


class PriceStreamManager:
    """
    Singleton-style manager for all active price subscriptions.

    One instance lives for the lifetime of the FastAPI app.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, TickerSubscription] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, ticker: str, ws: WebSocket) -> None:
        """
        Register a WebSocket connection as interested in a ticker.

        If this is the first subscriber for this ticker, starts a
        background refresh loop. Otherwise just adds to existing
        connection set.
        """
        ticker = ticker.upper()
        async with self._lock:
            if ticker not in self._subscriptions:
                self._subscriptions[ticker] = TickerSubscription(ticker=ticker)
                log.info("price_stream_new_ticker", ticker=ticker)

            sub = self._subscriptions[ticker]
            sub.connections.add(ws)

            if sub.refresh_task is None or sub.refresh_task.done():
                sub.refresh_task = asyncio.create_task(self._refresh_loop(ticker))
                log.info("price_stream_loop_started", ticker=ticker)

    async def unsubscribe(self, ticker: str, ws: WebSocket) -> None:
        """
        Remove a WebSocket connection from a ticker's subscriber set.

        If no subscribers remain, the refresh loop will notice on
        its next iteration and stop itself.
        """
        ticker = ticker.upper()
        async with self._lock:
            sub = self._subscriptions.get(ticker)
            if sub is None:
                return
            sub.connections.discard(ws)
            log.info(
                "price_stream_unsubscribed",
                ticker=ticker,
                remaining=len(sub.connections),
            )

    async def unsubscribe_all(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from every ticker it was watching."""
        async with self._lock:
            for sub in self._subscriptions.values():
                sub.connections.discard(ws)

    def active_tickers(self) -> list[str]:
        """Return tickers currently being refreshed (have subscribers)."""
        return [t for t, sub in self._subscriptions.items() if len(sub.connections) > 0]

    async def _refresh_loop(self, ticker: str) -> None:
        """
        Background loop: fetch a fresh price every REFRESH_INTERVAL_SECONDS
        and broadcast to all subscribers, for as long as subscribers exist.

        Stops itself once a ticker has had zero subscribers for
        STALE_THRESHOLD_SECONDS, freeing resources and respecting
        yFinance rate limits.
        """
        zero_subscriber_since: float | None = None

        while True:
            await asyncio.sleep(REFRESH_INTERVAL_SECONDS)

            sub = self._subscriptions.get(ticker)
            if sub is None:
                return

            if len(sub.connections) == 0:
                if zero_subscriber_since is None:
                    zero_subscriber_since = time.time()
                elif time.time() - zero_subscriber_since > STALE_THRESHOLD_SECONDS:
                    log.info("price_stream_loop_stopped", ticker=ticker)
                    async with self._lock:
                        self._subscriptions.pop(ticker, None)
                    return
                continue
            else:
                zero_subscriber_since = None

            try:
                price_data = await self._fetch_price(ticker)
            except Exception as e:
                log.warning("price_stream_fetch_failed", ticker=ticker, error=str(e))
                continue

            if price_data is None:
                continue

            price, change_pct = price_data
            sub.last_price = price
            sub.last_change_pct = change_pct
            sub.last_updated = time.time()

            await self._broadcast(sub, price, change_pct)

    async def _fetch_price(self, ticker: str) -> tuple[float, float] | None:
        """
        Fetch current price and % change from yFinance.

        Runs in a thread executor since yfinance is synchronous —
        prevents blocking the asyncio event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_price_sync, ticker)

    @staticmethod
    def _fetch_price_sync(ticker: str) -> tuple[float, float] | None:
        """Synchronous yFinance fetch — called via executor."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            price = float(info.get("lastPrice") or 0.0)
            prev_close = float(info.get("previousClose") or 0.0)

            if price <= 0 or prev_close <= 0:
                return None

            change_pct = ((price - prev_close) / prev_close) * 100
            return round(price, 4), round(change_pct, 4)
        except Exception:
            return None

    async def _broadcast(
        self,
        sub: TickerSubscription,
        price: float,
        change_pct: float,
    ) -> None:
        """Send price update to every connection subscribed to this ticker."""
        message = {
            "type": "price_update",
            "ticker": sub.ticker,
            "price": price,
            "change_pct": change_pct,
            "timestamp": time.time(),
        }

        dead_connections = set()
        for ws in sub.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.add(ws)

        for ws in dead_connections:
            sub.connections.discard(ws)


# Module-level singleton — one instance for the entire app lifetime
price_stream_manager = PriceStreamManager()
