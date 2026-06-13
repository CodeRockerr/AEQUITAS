"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Spinner } from "@/components/ui/Spinner";
import { backtestApi, type BacktestResponse } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

const TICKERS = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA"];
const STRATEGIES = [
  {
    id: "rsi",
    label: "RSI Mean-Reversion",
    desc: "Buy oversold, sell overbought",
  },
  { id: "macd", label: "MACD Crossover", desc: "Momentum trend-following" },
  {
    id: "bollinger",
    label: "Bollinger Mean-Rev",
    desc: "Price band breakout/reversion",
  },
];

// Synthetic equity curve from backtest stats
function buildEquityCurve(
  result: BacktestResponse,
): { day: number; value: number; bh: number }[] {
  const n = Math.min(result.n_bars, 252);
  const dailyReturn = result.annual_return_pct / 100 / 252;
  const bhDaily = result.benchmark_return_pct / 100 / n;
  const data = [];
  let val = 10000;
  let bh = 10000;
  for (let i = 0; i < n; i++) {
    const noise =
      ((Math.random() - 0.5) * (result.annual_volatility_pct / 100) * 10000) /
      Math.sqrt(252);
    val = val * (1 + dailyReturn) + noise;
    bh = bh * (1 + bhDaily);
    data.push({ day: i + 1, value: Math.round(val), bh: Math.round(bh) });
  }
  return data;
}

export default function BacktestsPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [strategy, setStrategy] = useState("rsi");
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await backtestApi.run(ticker, strategy);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setLoading(false);
    }
  }

  const equityCurve = result ? buildEquityCurve(result) : [];
  const alphaPositive = result && result.alpha_pct >= 0;

  return (
    <div style={{ minHeight: "100vh" }}>
      <PageHeader
        title="Backtests"
        subtitle="STRATEGY PERFORMANCE ANALYSIS"
        serif
      />

      <div style={{ padding: "32px 40px" }}>
        {/* Controls */}
        <div
          className="card"
          style={{ padding: "20px 24px", marginBottom: "24px" }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "auto 1fr auto",
              gap: "20px",
              alignItems: "end",
            }}
          >
            <div>
              <div className="stat-label" style={{ marginBottom: "8px" }}>
                Ticker
              </div>
              <div style={{ display: "flex", gap: "6px" }}>
                {TICKERS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTicker(t)}
                    className="btn"
                    style={{
                      background:
                        t === ticker ? "var(--text-primary)" : "transparent",
                      color:
                        t === ticker
                          ? "var(--text-inverse)"
                          : "var(--text-secondary)",
                      borderColor:
                        t === ticker
                          ? "var(--text-primary)"
                          : "var(--border-default)",
                      padding: "6px 10px",
                      fontSize: "11px",
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="stat-label" style={{ marginBottom: "8px" }}>
                Strategy
              </div>
              <div style={{ display: "flex", gap: "6px" }}>
                {STRATEGIES.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setStrategy(s.id)}
                    className="btn"
                    style={{
                      background:
                        s.id === strategy
                          ? "var(--text-primary)"
                          : "transparent",
                      color:
                        s.id === strategy
                          ? "var(--text-inverse)"
                          : "var(--text-secondary)",
                      borderColor:
                        s.id === strategy
                          ? "var(--text-primary)"
                          : "var(--border-default)",
                      padding: "6px 12px",
                      fontSize: "11px",
                      flexDirection: "column",
                      alignItems: "flex-start",
                      gap: "2px",
                      height: "auto",
                    }}
                  >
                    <span>{s.label}</span>
                    <span style={{ fontSize: "9px", opacity: 0.6 }}>
                      {s.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => void run()}
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Spinner size={12} /> Running...
                </>
              ) : (
                "Run Backtest →"
              )}
            </button>
          </div>
        </div>

        {error && (
          <div
            style={{
              background: "var(--accent-red-bg)",
              border:
                "1px solid color-mix(in srgb, var(--accent-red) 30%, transparent)",
              borderRadius: "var(--radius-md)",
              padding: "12px 16px",
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "var(--accent-red)",
              marginBottom: "24px",
            }}
          >
            {error}
          </div>
        )}

        {result && (
          <>
            {/* Stats */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                gap: "12px",
                marginBottom: "24px",
              }}
            >
              <StatCard
                label="Total Return"
                value={`${result.total_return_pct >= 0 ? "+" : ""}${result.total_return_pct.toFixed(1)}%`}
                accent={result.total_return_pct >= 0 ? "green" : "red"}
                delay={0}
              />
              <StatCard
                label="Alpha"
                value={`${alphaPositive ? "+" : ""}${result.alpha_pct.toFixed(1)}%`}
                sub="vs buy-and-hold"
                accent={alphaPositive ? "green" : "red"}
                delay={60}
              />
              <StatCard
                label="Sharpe"
                value={result.sharpe_ratio.toFixed(2)}
                accent={
                  result.sharpe_ratio > 1
                    ? "green"
                    : result.sharpe_ratio > 0
                      ? "amber"
                      : "red"
                }
                delay={120}
              />
              <StatCard
                label="Max Drawdown"
                value={`${result.max_drawdown_pct.toFixed(1)}%`}
                accent="red"
                delay={180}
              />
              <StatCard
                label="Win Rate"
                value={`${result.win_rate_pct.toFixed(0)}%`}
                sub={`${result.n_trades} trades`}
                delay={240}
              />
              <StatCard
                label="Sortino"
                value={result.sortino_ratio.toFixed(2)}
                delay={300}
              />
            </div>

            {/* Equity curve */}
            <div
              className="card animate-fade-up"
              style={{ padding: "24px", marginBottom: "16px" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      letterSpacing: "0.1em",
                      color: "var(--text-tertiary)",
                      textTransform: "uppercase",
                      marginBottom: "4px",
                    }}
                  >
                    Equity Curve · $10,000 Initial Capital
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: "14px",
                      color: "var(--text-primary)",
                      fontWeight: "500",
                    }}
                  >
                    {result.strategy}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "16px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <div
                      style={{
                        width: "12px",
                        height: "2px",
                        background: "var(--accent-green)",
                      }}
                    />
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10px",
                        color: "var(--text-tertiary)",
                      }}
                    >
                      Strategy
                    </span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                    }}
                  >
                    <div
                      style={{
                        width: "12px",
                        height: "2px",
                        background: "var(--border-strong)",
                        borderTop: "1px dashed",
                      }}
                    />
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10px",
                        color: "var(--text-tertiary)",
                      }}
                    >
                      Buy & Hold
                    </span>
                  </div>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={260}>
                <LineChart
                  data={equityCurve}
                  margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                >
                  <XAxis dataKey="day" hide />
                  <YAxis
                    tickFormatter={(value: number) => [
                      `$${value.toLocaleString()}`,
                      "",
                    ]}
                    tick={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      fill: "var(--text-tertiary)",
                    }}
                    axisLine={false}
                    tickLine={false}
                    width={44}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-default)",
                      borderRadius: "var(--radius-md)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                    }}
                    formatter={(value: number) => [
                      `$${value.toLocaleString()}`,
                      "",
                    ]}
                    labelFormatter={(l: number) => `Day ${l}`}
                  />
                  <ReferenceLine
                    y={10000}
                    stroke="var(--border-default)"
                    strokeDasharray="3 3"
                  />
                  <Line
                    type="monotone"
                    dataKey="bh"
                    stroke="var(--border-strong)"
                    strokeWidth={1}
                    dot={false}
                    strokeDasharray="4 4"
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="var(--accent-green)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Summary */}
            <div
              className="card animate-fade-up anim-delay-2"
              style={{
                padding: "16px 20px",
                background: "var(--bg-elevated)",
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  lineHeight: "1.7",
                }}
              >
                {result.summary}
              </div>
            </div>
          </>
        )}

        {!result && !loading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "80px 0",
              color: "var(--text-tertiary)",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "32px",
                marginBottom: "12px",
              }}
            >
              ◫
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                letterSpacing: "0.06em",
              }}
            >
              Select a ticker and strategy, then run the backtest
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
