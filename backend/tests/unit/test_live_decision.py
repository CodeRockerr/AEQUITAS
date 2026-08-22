"""
AEQUITAS - Tests for the live trading decision-latency WebSocket:
default synthetic feed, real-ticker replay, cycling once history is
exhausted, and the insufficient-history error path.
"""

import math
from datetime import datetime, timedelta

import pytest
from fastapi import WebSocketDisconnect

from app.api.v1 import live_decision
from app.api.v1.live_decision import RSI_PERIOD, websocket_live_decision


class _FakeLiveWebSocket:
    """Stands in for a real WebSocket: records every sent message and
    disconnects (like a real client closing the tab) once `max_messages`
    have been sent, so the endpoint's `while True` loop terminates."""

    def __init__(self, max_messages: int) -> None:
        self.sent: list[dict] = []
        self._max = max_messages
        self.closed = False

    async def accept(self) -> None:
        pass

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)
        if len(self.sent) >= self._max:
            raise WebSocketDisconnect()

    async def close(self) -> None:
        self.closed = True


class _FakeOhlcvRow:
    def __init__(self, time: datetime, price: float) -> None:
        self.time = time
        self.open = price
        self.high = price * 1.01
        self.low = price * 0.99
        self.close = price
        self.volume = 1_000_000


class _FakeOhlcvResult:
    def __init__(self, rows: list[_FakeOhlcvRow]) -> None:
        self._rows = rows

    def all(self) -> list[_FakeOhlcvRow]:
        return self._rows


class _FakeOhlcvDB:
    def __init__(self, rows: list[_FakeOhlcvRow]) -> None:
        self._rows = rows

    async def execute(self, *_args: object, **_kwargs: object) -> _FakeOhlcvResult:
        return _FakeOhlcvResult(self._rows)


def _sine_wave_rows(n: int) -> list[_FakeOhlcvRow]:
    # Sine-wave oscillation, not monotonic - a strictly-increasing series
    # has zero down-days ever, a real edge case in the RSI kernel (see
    # test_benchmark_endpoints.py for the same fixture pattern).
    base = datetime(2020, 1, 1)
    return [
        _FakeOhlcvRow(base + timedelta(days=i), 100.0 + 10 * math.sin(i / 8) + i * 0.05)
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def _no_real_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    # The endpoint sleeps TICK_INTERVAL_SECONDS between ticks - tests need
    # hundreds of ticks (to exercise cycling) without actually waiting.
    monkeypatch.setattr(live_decision, "TICK_INTERVAL_SECONDS", 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synthetic_feed_has_null_ticker_and_warms_up_first() -> None:
    ws = _FakeLiveWebSocket(max_messages=RSI_PERIOD + 3)

    await websocket_live_decision(ws, ticker=None, db=None)  # type: ignore[arg-type]

    assert all(m["ticker"] is None for m in ws.sent)
    assert [m["decision"] for m in ws.sent[:RSI_PERIOD]] == ["WARMING_UP"] * RSI_PERIOD
    assert ws.sent[RSI_PERIOD]["decision"] != "WARMING_UP"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ticker_replay_uses_real_closes_in_order() -> None:
    rows = _sine_wave_rows(300)
    db = _FakeOhlcvDB(rows)
    ws = _FakeLiveWebSocket(max_messages=RSI_PERIOD + 3)

    await websocket_live_decision(ws, ticker="aapl", db=db)  # type: ignore[arg-type]

    assert all(m["ticker"] == "AAPL" for m in ws.sent)
    # First tick replays the first real close (rounded the same way the
    # endpoint rounds every price).
    assert ws.sent[0]["price"] == round(rows[0].close, 4)
    assert ws.sent[1]["price"] == round(rows[1].close, 4)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ticker_replay_cycles_once_history_is_exhausted() -> None:
    rows = _sine_wave_rows(300)
    db = _FakeOhlcvDB(rows)
    # Ask for more ticks than there are real bars, to force a wraparound.
    ws = _FakeLiveWebSocket(max_messages=len(rows) + 5)

    await websocket_live_decision(ws, ticker="aapl", db=db)  # type: ignore[arg-type]

    assert ws.sent[0]["price"] == ws.sent[len(rows)]["price"]
    assert ws.sent[1]["price"] == ws.sent[len(rows) + 1]["price"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ticker_with_insufficient_history_sends_error_and_closes() -> None:
    db = _FakeOhlcvDB(_sine_wave_rows(50))  # below _fetch_real_ohlcv's 300-bar floor
    ws = _FakeLiveWebSocket(max_messages=100)

    await websocket_live_decision(ws, ticker="aapl", db=db)  # type: ignore[arg-type]

    assert ws.sent == [{"type": "error", "detail": ws.sent[0]["detail"]}]
    assert ws.closed is True
