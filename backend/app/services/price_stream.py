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

Market-closed handling:
  yfinance's fast_info can return stale/zero values when markets are
  closed (weekends, holidays, pre-market). When that happens, we fall
  back to the most recent daily close stored in our own database,
  so the UI always shows the last known real price instead of a gap.
"""

import asyncio
import time
from dataclasses import dataclass, field

import structlog
import yfinance as yf  # type: ignore[import-untyped]
from fastapi import WebSocket
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.market_data import OHLCVBar

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
    is_live: bool = True  # False when using fallback DB price (market closed)
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

        Immediately sends a snapshot (live or last-known) so the
        client doesn't wait a full refresh cycle for first data.
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

        # Send an immediate snapshot rather than waiting for the next tick
        await self._send_immediate_snapshot(ticker, ws)

    async def _send_immediate_snapshot(self, ticker: str, ws: WebSocket) -> None:
        """Fetch and send a price right away on subscribe, instead of waiting."""
        try:
            price_data = await self._fetch_price_with_fallback(ticker)
        except Exception as e:
            log.warning("price_stream_snapshot_failed", ticker=ticker, error=str(e))
            return

        if price_data is None:
            return

        price, change_pct, is_live = price_data
        sub = self._subscriptions.get(ticker)
        if sub is not None:
            sub.last_price = price
            sub.last_change_pct = change_pct
            sub.is_live = is_live
            sub.last_updated = time.time()

        try:
            await ws.send_json(
                {
                    "type": "price_update",
                    "ticker": ticker,
                    "price": price,
                    "change_pct": change_pct,
                    "is_live": is_live,
                    "timestamp": time.time(),
                }
            )
        except Exception:
            pass

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
                price_data = await self._fetch_price_with_fallback(ticker)
            except Exception as e:
                log.warning("price_stream_fetch_failed", ticker=ticker, error=str(e))
                continue

            if price_data is None:
                continue

            price, change_pct, is_live = price_data
            sub.last_price = price
            sub.last_change_pct = change_pct
            sub.is_live = is_live
            sub.last_updated = time.time()

            await self._broadcast(sub, price, change_pct, is_live)

    async def _fetch_price_with_fallback(
        self, ticker: str
    ) -> tuple[float, float, bool] | None:
        """
        Fetch current price, falling back to the last known daily
        close from our own database when the live feed has nothing
        (market closed, weekend, holiday, or yfinance hiccup).

        Returns (price, change_pct, is_live) or None if neither
        source has any data at all.
        """
        live = await self._fetch_price_live(ticker)
        if live is not None:
            return live[0], live[1], True

        fallback = await self._fetch_price_from_db(ticker)
        if fallback is not None:
            return fallback[0], fallback[1], False

        return None

    async def _fetch_price_live(self, ticker: str) -> tuple[float, float] | None:
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

    async def _fetch_price_from_db(self, ticker: str) -> tuple[float, float] | None:
        """
        Fall back to the two most recent daily closes already stored
        in TimescaleDB — used when markets are closed and yfinance's
        live feed has nothing current to offer.

        change_pct here is computed from the last two stored closes,
        i.e. the most recent completed trading day's move.
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(OHLCVBar.close)
                    .where(OHLCVBar.ticker == ticker, OHLCVBar.interval == "1d")
                    .order_by(OHLCVBar.time.desc())
                    .limit(2)
                )
                rows = result.scalars().all()
        except Exception as e:
            log.warning("price_stream_db_fallback_failed", ticker=ticker, error=str(e))
            return None

        if not rows:
            return None

        latest = float(rows[0])
        if len(rows) < 2:
            return round(latest, 4), 0.0

        previous = float(rows[1])
        if previous <= 0:
            return round(latest, 4), 0.0

        change_pct = ((latest - previous) / previous) * 100
        return round(latest, 4), round(change_pct, 4)

    async def _broadcast(
        self,
        sub: TickerSubscription,
        price: float,
        change_pct: float,
        is_live: bool,
    ) -> None:
        """Send price update to every connection subscribed to this ticker."""
        message = {
            "type": "price_update",
            "ticker": sub.ticker,
            "price": price,
            "change_pct": change_pct,
            "is_live": is_live,
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
