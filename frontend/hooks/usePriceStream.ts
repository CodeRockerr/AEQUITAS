"use client";

/**
 * AEQUITAS — Real-time price streaming hook.
 *
 * Opens one WebSocket connection and lets you subscribe to
 * multiple tickers. Automatically reconnects on disconnect.
 *
 * isLive distinguishes a genuinely live tick from a fallback
 * last-known-close (used when markets are closed — weekends,
 * holidays, after hours).
 *
 * Subscriptions called before the socket finishes connecting are
 * queued in subscribedRef and flushed on open — this is the fix
 * for a race condition where subscribe() calls fired immediately
 * on mount were silently dropped because the WebSocket hadn't
 * reached OPEN state yet (readyState !== WebSocket.OPEN).
 *
 * Usage:
 *   const { prices, subscribe, unsubscribe, connected } = usePriceStream();
 *   useEffect(() => { subscribe("AAPL"); return () => unsubscribe("AAPL"); }, []);
 *   const aapl = prices["AAPL"];  // { price, changePct, timestamp, isLive }
 */

import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
    /^http/,
    "ws",
  ) + "/ws/prices";

export interface LivePrice {
  price: number;
  changePct: number;
  timestamp: number;
  isLive: boolean;
}

interface ServerMessage {
  type: "price_update" | "subscribed" | "unsubscribed" | "error";
  ticker?: string;
  price?: number;
  change_pct?: number;
  is_live?: boolean;
  timestamp?: number;
  message?: string;
}

const RECONNECT_DELAY_MS = 3000;

export function usePriceStream() {
  const [prices, setPrices] = useState<Record<string, LivePrice>>({});
  const [connected, setConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  // Tracks every ticker we WANT to be subscribed to, regardless of
  // whether the socket is currently open. Always the source of truth.
  const subscribedRef = useRef<Set<string>>(new Set());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isUnmountedRef = useRef(false);

  const flushSubscriptions = useCallback((ws: WebSocket) => {
    for (const ticker of subscribedRef.current) {
      ws.send(JSON.stringify({ action: "subscribe", ticker }));
    }
  }, []);

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Flush every ticker requested so far — including any that
      // called subscribe() before this connection finished opening.
      flushSubscriptions(ws);
    };

    ws.onmessage = (event) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data);
        if (
          msg.type === "price_update" &&
          msg.ticker &&
          msg.price !== undefined
        ) {
          setPrices((prev) => ({
            ...prev,
            [msg.ticker as string]: {
              price: msg.price as number,
              changePct: msg.change_pct ?? 0,
              timestamp: msg.timestamp ?? Date.now() / 1000,
              isLive: msg.is_live ?? true,
            },
          }));
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (!isUnmountedRef.current) {
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [flushSubscriptions]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();
    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const subscribe = useCallback((ticker: string) => {
    const t = ticker.toUpperCase();
    subscribedRef.current.add(t);
    // If the socket is already open, send immediately.
    // If not, this ticker is already in subscribedRef and will be
    // flushed automatically once onopen fires — never silently lost.
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "subscribe", ticker: t }));
    }
  }, []);

  const unsubscribe = useCallback((ticker: string) => {
    const t = ticker.toUpperCase();
    subscribedRef.current.delete(t);
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "unsubscribe", ticker: t }));
    }
    setPrices((prev) => {
      const next = { ...prev };
      delete next[t];
      return next;
    });
  }, []);

  return { prices, subscribe, unsubscribe, connected };
}
