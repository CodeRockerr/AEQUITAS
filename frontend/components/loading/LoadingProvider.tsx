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
const MAX_WAIT_MS = 90000; // dismiss automatically after 90s — Render free tier cold start can take ~50-60s

export function LoadingProvider({ children }: { children: ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  const dismiss = () => {
    setDismissed(true);
    setIsLoading(false);
  };

  useEffect(() => {
    // Don't show loading screen on subsequent visits — only on first
    // page load where the API is genuinely cold-starting on Render.
    // We poll the health endpoint until it responds, then dismiss.
    let cancelled = false;

    // Hard timeout — never block forever
    const maxTimer = setTimeout(() => {
      if (!cancelled) dismiss();
    }, MAX_WAIT_MS);

    async function pollHealth() {
      while (!cancelled) {
        try {
          const res = await fetch(`${API_BASE}/health`, {
            signal: AbortSignal.timeout(4000),
          });
          if (res.ok && !cancelled) {
            clearTimeout(maxTimer);
            dismiss();
            return;
          }
        } catch {
          // API not ready yet — keep polling
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }

    void pollHealth();

    return () => {
      cancelled = true;
      clearTimeout(maxTimer);
    };
  }, []);

  const show = isLoading && !dismissed;

  return (
    <LoadingContext.Provider value={{ isLoading: show, dismiss }}>
      {show && <LoadingScreen onDismiss={dismiss} />}
      {/* Render children behind — they load in parallel, ready instantly on dismiss */}
      <div style={{ visibility: show ? "hidden" : "visible" }}>{children}</div>
    </LoadingContext.Provider>
  );
}
