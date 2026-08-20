"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { LoadingScreen } from "./LoadingScreen";

interface LoadingContextValue {
  isLoading: boolean;
  dismiss: () => void;
}

const LoadingContext = createContext<LoadingContextValue>({
  isLoading: false,
  dismiss: () => {},
});

export const useLoading = () => useContext(LoadingContext);

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MAX_WAIT_MS = 90000; // hard safety-net cap if the API is ever genuinely slow to respond
// The API now stays warm (keep-warm workflow) and typically answers almost
// instantly, which used to mean this screen - built to show off the fun
// fact / mini-game / portfolio+resume links while a slow cold start masked
// the wait - flashed by too fast for anyone to actually see any of it.
// Holding it up for a deliberate minimum (picked once per visit, 30-35s)
// keeps that content genuinely visible; Skip still bypasses this instantly
// for anyone in a hurry.
const MIN_DISPLAY_MS_RANGE: [number, number] = [30000, 35000];

export function LoadingProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  // Tracks whether we gave up via the hard timeout rather than a real
  // successful health check, so we can tell the user the connection may
  // still be bad instead of dropping them into the app identically either way.
  const [connectionFailed, setConnectionFailed] = useState(false);

  const dismiss = (reason: "success" | "timeout" = "success") => {
    if (reason === "timeout") setConnectionFailed(true);
    setDismissed(true);
    setIsLoading(false);
  };

  useEffect(() => {
    // Don't show loading screen on subsequent visits, only on first
    // page load where the API is genuinely cold-starting on Render.
    // We poll the health endpoint until it responds, then dismiss -
    // but never before minDisplayMs has elapsed (see MIN_DISPLAY_MS_RANGE).
    let cancelled = false;
    let finalDismissTimer: ReturnType<typeof setTimeout> | null = null;
    const startedAt = Date.now();
    const minDisplayMs =
      MIN_DISPLAY_MS_RANGE[0] +
      Math.random() * (MIN_DISPLAY_MS_RANGE[1] - MIN_DISPLAY_MS_RANGE[0]);

    // Hard timeout, never block forever
    const maxTimer = setTimeout(() => {
      if (!cancelled) dismiss("timeout");
    }, MAX_WAIT_MS);

    function finishSuccessfully() {
      const fire = () => {
        if (!cancelled) {
          clearTimeout(maxTimer);
          dismiss("success");
        }
      };
      const remaining = minDisplayMs - (Date.now() - startedAt);
      if (remaining <= 0) {
        fire();
      } else {
        finalDismissTimer = setTimeout(fire, remaining);
      }
    }

    async function pollHealth() {
      while (!cancelled) {
        try {
          const res = await fetch(`${API_BASE}/health`, {
            signal: AbortSignal.timeout(4000),
          });
          if (res.ok && !cancelled) {
            finishSuccessfully();
            return;
          }
        } catch {
          // API not ready yet, keep polling
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }

    void pollHealth();

    return () => {
      cancelled = true;
      clearTimeout(maxTimer);
      if (finalDismissTimer) clearTimeout(finalDismissTimer);
    };
  }, []);

  const show = isLoading && !dismissed;

  return (
    <LoadingContext.Provider
      value={{ isLoading: show, dismiss: () => dismiss("success") }}
    >
      {show && <LoadingScreen onDismiss={() => dismiss("success")} />}
      {/* Render children behind, they load in parallel, ready instantly on dismiss */}
      <div style={{ visibility: show ? "hidden" : "visible" }}>{children}</div>
      {connectionFailed && !show && (
        <div
          role="status"
          style={{
            position: "fixed",
            bottom: "16px",
            right: "16px",
            zIndex: 9998,
            maxWidth: "320px",
            background: "var(--accent-amber-bg)",
            border:
              "1px solid color-mix(in srgb, var(--accent-amber) 30%, transparent)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-md)",
            padding: "10px 14px",
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--accent-amber)",
            lineHeight: 1.5,
          }}
        >
          Having trouble connecting to the API. Some data may be unavailable,
          try refreshing in a moment.
        </div>
      )}
    </LoadingContext.Provider>
  );
}
