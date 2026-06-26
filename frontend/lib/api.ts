/**
 * AEQUITAS — Typed API client
 * All calls to the FastAPI backend go through this module.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Generic fetcher ───────────────────────────────────────────
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ─────────────────────────────────────────────────────
export interface HealthResponse {
  status: string;
  env: string;
  version: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface SignalResponse {
  ticker: string;
  combined_signal: number;
  direction: string;
  signals: {
    rsi: { value: number; raw: number; note: string };
    macd: { value: number; raw: number; note: string };
    bollinger: { value: number; raw: number; note: string };
  };
}

export interface RegimeResponse {
  ticker: string;
  current_regime: string;
  current_regime_prob: number;
  current_regime_color: string;
  regime_sequence: string[];
  regime_stats: Record<
    string,
    {
      mean_daily_return: number;
      daily_volatility: number;
      days_in_regime: number;
      pct_of_time: number;
      avg_duration_days: number;
    }
  >;
  transition_matrix: number[][];
  n_observations: number;
}

export interface ForecastResponse {
  ticker: string;
  predicted_return_pct: string;
  direction: string;
  confidence: number;
  top_drivers: Array<{
    feature: string;
    shap_value: number;
    direction: string;
    magnitude: number;
  }>;
  model_metrics: { mae: number; rmse: number; directional_accuracy: string };
  n_training_samples: number;
}

export interface BacktestResponse {
  ticker: string;
  strategy: string;
  total_return_pct: number;
  annual_return_pct: number;
  annual_volatility_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  win_rate_pct: number;
  n_trades: number;
  avg_trade_duration_days: number;
  benchmark_return_pct: number;
  alpha_pct: number;
  start_date: string;
  end_date: string;
  n_bars: number;
  summary: string;
}

export interface VaRResponse {
  var: number;
  cvar: number;
  confidence_level: number;
  horizon_days: number;
  method: string;
  portfolio_value: number;
  interpretation: string;
}

export interface ResearchResponse {
  ticker: string;
  company_summary: string;
  filing_citations: string[];
  current_regime: string;
  regime_confidence: number;
  signal_direction: string;
  signal_score: number;
  predicted_return_pct: string;
  var_95: number;
  top_shap_drivers: Array<{
    feature: string;
    shap_value: number;
    direction: string;
    magnitude: number;
  }>;
  final_thesis: string;
  thesis_sentiment: string;
  confidence_score: number;
  critique: string;
  revision_count: number;
  errors: string[];
}

export interface BlackScholesResponse {
  price: number;
  greeks: {
    delta: number;
    gamma: number;
    vega: number;
    theta: number;
    rho: number;
  };
  d1: number;
  d2: number;
  option_type: string;
  moneyness: string;
}

// ── API modules ───────────────────────────────────────────────
export const healthApi = {
  check: () => apiFetch<HealthResponse>("/health"),
};

export const signalsApi = {
  get: (ticker: string) =>
    apiFetch<SignalResponse>(`/api/v1/signals/${ticker}`),
};

export const mlApi = {
  regime: (ticker: string) =>
    apiFetch<RegimeResponse>(`/api/v1/ml/regime/${ticker}`, { method: "POST" }),
  forecast: (ticker: string) =>
    apiFetch<ForecastResponse>(`/api/v1/ml/forecast/${ticker}`, {
      method: "POST",
    }),
};

export const backtestApi = {
  run: (ticker: string, strategy: string) =>
    apiFetch<BacktestResponse>(`/api/v1/backtest/${ticker}/${strategy}`, {
      method: "POST",
    }),
};

export const riskApi = {
  var: (ticker: string, portfolioValue: number, method = "historical") =>
    apiFetch<VaRResponse>("/api/v1/risk/var", {
      method: "POST",
      body: JSON.stringify({ ticker, portfolio_value: portfolioValue, method }),
    }),
};

export const agentsApi = {
  research: (ticker: string) =>
    apiFetch<ResearchResponse>(`/api/v1/agents/research/${ticker}`, {
      method: "POST",
    }),
};

export const pricingApi = {
  blackScholes: (params: {
    spot: number;
    strike: number;
    rate: number;
    volatility: number;
    expiry: number;
    option_type: string;
  }) =>
    apiFetch<BlackScholesResponse>("/api/v1/pricing/black-scholes", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};

// ── Add this to lib/api.ts ─────────────────────────────────────

export interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoryResponse {
  ticker: string;
  range: string;
  candles: Candle[];
  n_candles: number;
  first_date: string | null;
  last_date: string | null;
}

export const historyApi = {
  get: (ticker: string, range: "1mo" | "6mo" | "1y" | "5y" | "max" = "1y") =>
    apiFetch<HistoryResponse>(`/api/v1/history/${ticker}?range_=${range}`),
};
