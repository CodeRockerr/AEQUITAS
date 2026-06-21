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
  const subscribedRef = useRef<Set<string>>(new Set());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Re-subscribe to anything that was subscribed before a reconnect
      for (const ticker of subscribedRef.current) {
        ws.send(JSON.stringify({ action: "subscribe", ticker }));
      }
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
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((ticker: string) => {
    const t = ticker.toUpperCase();
    subscribedRef.current.add(t);
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
