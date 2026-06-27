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

// ── Health ───────────────────────────────────────────────────
export interface HealthResponse {
  status: string;
  env: string;
  version: string;
  uptime_seconds: number;
  timestamp: string;
}

export const healthApi = {
  check: () => apiFetch<HealthResponse>("/health"),
};

// ── Signals ──────────────────────────────────────────────────
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

export const signalsApi = {
  get: (ticker: string) =>
    apiFetch<SignalResponse>(`/api/v1/signals/${ticker}`),
};

// ── ML (regime + forecast) ──────────────────────────────────
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

export const mlApi = {
  regime: (ticker: string) =>
    apiFetch<RegimeResponse>(`/api/v1/ml/regime/${ticker}`, { method: "POST" }),
  forecast: (ticker: string) =>
    apiFetch<ForecastResponse>(`/api/v1/ml/forecast/${ticker}`, {
      method: "POST",
    }),
};

// ── Backtesting ──────────────────────────────────────────────
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

export const backtestApi = {
  run: (ticker: string, strategy: string) =>
    apiFetch<BacktestResponse>(`/api/v1/backtest/${ticker}/${strategy}`, {
      method: "POST",
    }),
};

// ── Risk ─────────────────────────────────────────────────────
export interface VaRResponse {
  var: number;
  cvar: number;
  confidence_level: number;
  horizon_days: number;
  method: string;
  portfolio_value: number;
  interpretation: string;
}

export const riskApi = {
  var: (ticker: string, portfolioValue: number, method = "historical") =>
    apiFetch<VaRResponse>("/api/v1/risk/var", {
      method: "POST",
      body: JSON.stringify({ ticker, portfolio_value: portfolioValue, method }),
    }),
};

// ── Agents ───────────────────────────────────────────────────
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

export const agentsApi = {
  research: (ticker: string) =>
    apiFetch<ResearchResponse>(`/api/v1/agents/research/${ticker}`, {
      method: "POST",
    }),
};

// ── Pricing (Black-Scholes) ──────────────────────────────────
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

// ── Price History (candlestick charts) ───────────────────────
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

// ── Factor Model (Fama-French) ────────────────────────────────
export interface FactorModelResponse {
  ticker: string;
  alpha: number;
  alpha_pct: number;
  alpha_tstat: number;
  alpha_significant: boolean;
  beta_market: number;
  beta_smb: number;
  beta_hml: number;
  r_squared: number;
  residual_vol: number;
  interpretation: string;
}

export const factorModelApi = {
  run: (ticker: string) =>
    apiFetch<FactorModelResponse>(`/api/v1/factor-model/${ticker}`, {
      method: "POST",
    }),
};

// ── Execution Algorithms (TWAP/VWAP/IS) ───────────────────────
export interface ExecutionSlice {
  interval: number;
  start_time: string;
  end_time: string;
  shares: number;
  pct_of_order: number;
}

export interface ExecutionScheduleResponse {
  ticker: string;
  total_shares: number;
  n_intervals: number;
  algorithm: string;
  slices: ExecutionSlice[];
  expected_completion: string;
  participation_rate: number;
}

export const executionApi = {
  twap: (ticker: string, totalShares: number, nIntervals = 13) =>
    apiFetch<ExecutionScheduleResponse>(`/api/v1/execution/${ticker}/twap`, {
      method: "POST",
      body: JSON.stringify({
        total_shares: totalShares,
        n_intervals: nIntervals,
      }),
    }),
  vwap: (ticker: string, totalShares: number, nIntervals = 13) =>
    apiFetch<ExecutionScheduleResponse>(`/api/v1/execution/${ticker}/vwap`, {
      method: "POST",
      body: JSON.stringify({
        total_shares: totalShares,
        n_intervals: nIntervals,
      }),
    }),
  is: (ticker: string, totalShares: number, urgency: number, nIntervals = 13) =>
    apiFetch<ExecutionScheduleResponse>(`/api/v1/execution/${ticker}/is`, {
      method: "POST",
      body: JSON.stringify({
        total_shares: totalShares,
        n_intervals: nIntervals,
        urgency,
      }),
    }),
};

// ── Add this to lib/api.ts ─────────────────────────────────────

export interface NewsArticle {
  headline: string;
  source: string;
  url: string;
  published: string;
}

export interface NewsSentimentResponse {
  ticker: string;
  sentiment: string;
  sentiment_score: number;
  trend: string;
  confidence: number;
  summary: string;
  key_themes: string[];
  recent_articles: NewsArticle[];
  finnhub_sentiment_available: boolean;
  errors: string[];
}

export interface EarningsHistoryEntry {
  date: string;
  quarter: string;
  eps_actual: number | null;
  eps_estimate: number | null;
  eps_surprise_pct: number | null;
  revenue_actual: number | null;
  revenue_estimate: number | null;
}

export interface EarningsAnalysisResponse {
  ticker: string;
  next_earnings_date: string | null;
  last_earnings_beat: boolean | null;
  last_eps_surprise_pct: number | null;
  guidance_sentiment: string;
  analysis: string;
  key_metrics: Record<string, number | null>;
  earnings_history: EarningsHistoryEntry[];
  errors: string[];
}

export interface PortfolioAllocationOut {
  ticker: string;
  max_sharpe_weight: number;
  min_variance_weight: number;
}

export interface PairCointegrationOut {
  ticker_a: string;
  ticker_b: string;
  is_cointegrated: boolean;
  p_value: number;
  half_life: number;
}

export interface PortfolioConstructionResponse {
  tickers: string[];
  allocations: PortfolioAllocationOut[];
  max_sharpe_return: number;
  max_sharpe_vol: number;
  max_sharpe_ratio: number;
  min_variance_vol: number;
  cointegrated_pairs: PairCointegrationOut[];
  thesis: string;
  errors: string[];
}

export const extendedAgentsApi = {
  newsSentiment: (ticker: string) =>
    apiFetch<NewsSentimentResponse>(`/api/v1/agents/news-sentiment/${ticker}`, {
      method: "POST",
    }),
  earnings: (ticker: string) =>
    apiFetch<EarningsAnalysisResponse>(`/api/v1/agents/earnings/${ticker}`, {
      method: "POST",
    }),
  portfolio: (tickers: string[]) =>
    apiFetch<PortfolioConstructionResponse>("/api/v1/agents/portfolio", {
      method: "POST",
      body: JSON.stringify({ tickers }),
    }),
};
