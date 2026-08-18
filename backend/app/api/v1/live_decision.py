"""
AEQUITAS - Live trading decision-latency demo.

WebSocket endpoint that streams a synthetic tick-by-tick price feed and,
on every new tick, recomputes a buy/sell/hold RSI signal two ways -
pandas (app/algorithms/signals/momentum.py, the platform's real
signal-generation code) and the C++20 kernel (backend/cpp) - timing
each computation. Same RSI kernel already benchmarked in
/benchmark/kernels, framed as what it actually buys a trading system:
faster time-to-decision on every new bar.

No real broker, no real orders, no real money - a synthetic geometric
random walk only.

Protocol:
  Client connects to /ws/live-decision
  Server sends one message per tick:
    {"type": "tick", "seq": 42, "price": 101.23, "decision": "BUY",
     "signal": 0.42, "pandas_us": 210.4, "cpp_us": 8.1,
     "speedup": 26.0, "cpp_available": true}
"""

import asyncio
import time
from collections import deque

import numpy as np
import pandas as pd
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.algorithms.signals.momentum import rsi_signal

try:
    import aequitas_kernels as ck

    CPP_AVAILABLE = True
except ImportError:  # extension not built in this environment
    ck = None
    CPP_AVAILABLE = False

log = structlog.get_logger()
router = APIRouter()

TICK_INTERVAL_SECONDS = 0.4
BUFFER_SIZE = 250  # rolling window kept per connection - bounds decision latency
RSI_PERIOD = 14
BUY_THRESHOLD = 0.3
SELL_THRESHOLD = -0.3


def _decision(signal: float) -> str:
    if signal > BUY_THRESHOLD:
        return "BUY"
    if signal < SELL_THRESHOLD:
        return "SELL"
    return "HOLD"


@router.websocket("/ws/live-decision")
async def websocket_live_decision(websocket: WebSocket) -> None:
    """Synthetic live tick feed with a pandas-vs-C++ decision-latency race."""
    await websocket.accept()
    rng = np.random.default_rng()
    price = 100.0
    buffer: deque[float] = deque(maxlen=BUFFER_SIZE)
    seq = 0

    try:
        while True:
            price *= float(np.exp(rng.normal(0, 0.004)))
            buffer.append(price)
            seq += 1

            if len(buffer) < RSI_PERIOD + 1:
                await websocket.send_json(
                    {
                        "type": "tick",
                        "seq": seq,
                        "price": round(price, 4),
                        "decision": "WARMING_UP",
                        "signal": 0.0,
                        "pandas_us": None,
                        "cpp_us": None,
                        "speedup": None,
                        "cpp_available": CPP_AVAILABLE,
                    }
                )
                await asyncio.sleep(TICK_INTERVAL_SECONDS)
                continue

            arr = np.fromiter(buffer, dtype=float)

            t0 = time.perf_counter()
            p_result = rsi_signal(pd.Series(arr))
            pandas_us = (time.perf_counter() - t0) * 1e6

            signal = p_result.signal
            cpp_us = None
            speedup = None
            if CPP_AVAILABLE:
                t0 = time.perf_counter()
                cpp_rsi = float(ck.rsi(arr, RSI_PERIOD)[-1])
                cpp_us = (time.perf_counter() - t0) * 1e6
                if not np.isnan(cpp_rsi):
                    signal = -(cpp_rsi - 50) / 50
                speedup = round(pandas_us / cpp_us, 1) if cpp_us > 0 else None

            await websocket.send_json(
                {
                    "type": "tick",
                    "seq": seq,
                    "price": round(price, 4),
                    "decision": _decision(signal),
                    "signal": round(signal, 4),
                    "pandas_us": round(pandas_us, 1),
                    "cpp_us": round(cpp_us, 1) if cpp_us is not None else None,
                    "speedup": speedup,
                    "cpp_available": CPP_AVAILABLE,
                }
            )
            await asyncio.sleep(TICK_INTERVAL_SECONDS)

    except WebSocketDisconnect:
        log.info("live_decision_client_disconnected", seq=seq)
