/**
 * AEQUITAS — Typed API client
 *
 * All calls to the FastAPI backend go through this module.
 * Benefits:
 *  - One place to set the base URL, auth headers, error handling
 *  - TypeScript types for every response shape
 *  - Easy to mock in tests
 *
 * We'll expand this heavily in Week 7 when we build the dashboard.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Response types (mirror the Pydantic models in backend) ────
export interface HealthResponse {
  status: string;
  env: string;
  version: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface ReadinessResponse {
  status: string;
  checks: Record<string, string>;
}

// ── Generic fetcher with error handling ───────────────────────
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail ?? `API error: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Health API ────────────────────────────────────────────────
export const healthApi = {
  check: () => apiFetch<HealthResponse>("/health"),
  ready: () => apiFetch<ReadinessResponse>("/health/ready"),
};

// We'll add more API modules here as we build each feature:
// export const signalsApi = { ... }
// export const backtestApi = { ... }
// export const agentsApi = { ... }
