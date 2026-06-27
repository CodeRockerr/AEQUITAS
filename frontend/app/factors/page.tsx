"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  factorModelApi,
  executionApi,
  type FactorModelResponse,
  type ExecutionScheduleResponse,
} from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";

const TICKERS = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA"];
const EXEC_ALGOS = [
  { id: "twap", label: "TWAP", desc: "Equal shares per interval" },
  { id: "vwap", label: "VWAP", desc: "U-shaped intraday volume profile" },
  {
    id: "is",
    label: "Implementation Shortfall",
    desc: "Urgency-weighted front/back loading",
  },
] as const;

export default function FactorsPage() {
  // ── Factor model state ──────────────────────────────────────
  const [factorTicker, setFactorTicker] = useState("AAPL");
  const [factorResult, setFactorResult] = useState<FactorModelResponse | null>(
    null,
  );
  const [factorLoading, setFactorLoading] = useState(false);
  const [factorError, setFactorError] = useState<string | null>(null);

  // ── Execution scheduler state ───────────────────────────────
  const [execTicker, setExecTicker] = useState("AAPL");
  const [execAlgo, setExecAlgo] =
    useState<(typeof EXEC_ALGOS)[number]["id"]>("vwap");
  const [totalShares, setTotalShares] = useState("50000");
  const [urgency, setUrgency] = useState(0.5);
  const [execResult, setExecResult] =
    useState<ExecutionScheduleResponse | null>(null);
  const [execLoading, setExecLoading] = useState(false);
  const [execError, setExecError] = useState<string | null>(null);

  async function runFactorModel() {
    setFactorLoading(true);
    setFactorError(null);
    try {
      const r = await factorModelApi.run(factorTicker);
      setFactorResult(r);
    } catch (e) {
      setFactorError(
        e instanceof Error
          ? `${e.message} — make sure SPY, IWM, IVE, IWF are ingested as benchmarks.`
          : "Factor model failed",
      );
    } finally {
      setFactorLoading(false);
    }
  }

  async function runExecution() {
    setExecLoading(true);
    setExecError(null);
    const shares = parseInt(totalShares, 10) || 10000;
    try {
      let r: ExecutionScheduleResponse;
      if (execAlgo === "twap") r = await executionApi.twap(execTicker, shares);
      else if (execAlgo === "vwap")
        r = await executionApi.vwap(execTicker, shares);
      else r = await executionApi.is(execTicker, shares, urgency);
      setExecResult(r);
    } catch (e) {
      setExecError(
        e instanceof Error ? e.message : "Execution scheduling failed",
      );
    } finally {
      setExecLoading(false);
    }
  }

  const chartData =
    execResult?.slices.map((s) => ({
      interval: s.start_time,
      shares: s.shares,
    })) ?? [];

  return (
    <div style={{ minHeight: "100vh" }}>
      <PageHeader
        title="Factors & Execution"
        subtitle="FAMA-FRENCH · TWAP · VWAP · IMPLEMENTATION SHORTFALL"
        serif
      />

      <div style={{ padding: "32px 40px" }}>
        {/* ── Fama-French Factor Model ──────────────────────── */}
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            letterSpacing: "0.1em",
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            marginBottom: "12px",
          }}
        >
          Fama-French 3-Factor Model
        </div>

        <div
          className="card"
          style={{ padding: "20px 24px", marginBottom: "24px" }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "auto auto 1fr auto",
              gap: "16px",
              alignItems: "end",
            }}
          >
            <div>
              <div className="stat-label" style={{ marginBottom: "6px" }}>
                Ticker
              </div>
              <div style={{ display: "flex", gap: "4px" }}>
                {TICKERS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setFactorTicker(t)}
                    className="btn"
                    style={{
                      background:
                        t === factorTicker
                          ? "var(--text-primary)"
                          : "transparent",
                      color:
                        t === factorTicker
                          ? "var(--text-inverse)"
                          : "var(--text-secondary)",
                      borderColor:
                        t === factorTicker
                          ? "var(--text-primary)"
                          : "var(--border-default)",
                      padding: "5px 10px",
                      fontSize: "11px",
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div />
            <div />
            <button
              onClick={() => void runFactorModel()}
              className="btn btn-primary"
              disabled={factorLoading}
            >
              {factorLoading ? (
                <>
                  <Spinner size={12} /> Computing...
                </>
              ) : (
                "Run Factor Model →"
              )}
            </button>
          </div>
          <div
            style={{
              marginTop: "12px",
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              color: "var(--text-tertiary)",
            }}
          >
            Decomposes returns into market beta, size (SMB), and value (HML)
            exposures using SPY, IWM, IVE, IWF as factor proxies.
          </div>
        </div>

        {factorError && (
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
            {factorError}
          </div>
        )}

        {factorResult && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                gap: "12px",
                marginBottom: "20px",
              }}
            >
              <StatCard
                label="Alpha (annualised)"
                value={`${factorResult.alpha_pct >= 0 ? "+" : ""}${factorResult.alpha_pct.toFixed(2)}%`}
                sub={`t-stat: ${factorResult.alpha_tstat.toFixed(2)}`}
                accent={factorResult.alpha_pct >= 0 ? "green" : "red"}
                delay={0}
              />
              <StatCard
                label="Market Beta"
                value={factorResult.beta_market.toFixed(2)}
                sub={
                  factorResult.beta_market > 1
                    ? "More volatile than market"
                    : "Less volatile than market"
                }
                delay={60}
              />
              <StatCard
                label="SMB (Size)"
                value={`${factorResult.beta_smb >= 0 ? "+" : ""}${factorResult.beta_smb.toFixed(2)}`}
                sub={
                  factorResult.beta_smb > 0
                    ? "Small-cap tilt"
                    : "Large-cap tilt"
                }
                accent={factorResult.beta_smb >= 0 ? "blue" : "amber"}
                delay={120}
              />
              <StatCard
                label="HML (Value)"
                value={`${factorResult.beta_hml >= 0 ? "+" : ""}${factorResult.beta_hml.toFixed(2)}`}
                sub={factorResult.beta_hml > 0 ? "Value tilt" : "Growth tilt"}
                accent={factorResult.beta_hml >= 0 ? "blue" : "amber"}
                delay={180}
              />
              <StatCard
                label="R²"
                value={`${(factorResult.r_squared * 100).toFixed(1)}%`}
                sub="Variance explained"
                delay={240}
              />
            </div>

            <div
              className="card animate-fade-up"
              style={{ padding: "20px 24px", marginBottom: "32px" }}
            >
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  alignItems: "flex-start",
                }}
              >
                <Badge
                  variant={factorResult.alpha_significant ? "green" : "neutral"}
                >
                  {factorResult.alpha_significant
                    ? "Significant alpha"
                    : "Not significant"}
                </Badge>
              </div>
              <div
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                  lineHeight: "1.8",
                  marginTop: "12px",
                }}
              >
                {factorResult.interpretation}
              </div>
            </div>
          </>
        )}

        {/* ── Execution Scheduler ────────────────────────────── */}
        <div className="divider" style={{ marginBottom: "32px" }} />

        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            letterSpacing: "0.1em",
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            marginBottom: "12px",
          }}
        >
          Execution Scheduler
        </div>

        <div
          className="card"
          style={{ padding: "20px 24px", marginBottom: "24px" }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "auto auto 1fr",
              gap: "16px",
              marginBottom: "16px",
            }}
          >
            <div>
              <div className="stat-label" style={{ marginBottom: "6px" }}>
                Ticker
              </div>
              <div style={{ display: "flex", gap: "4px" }}>
                {TICKERS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setExecTicker(t)}
                    className="btn"
                    style={{
                      background:
                        t === execTicker
                          ? "var(--text-primary)"
                          : "transparent",
                      color:
                        t === execTicker
                          ? "var(--text-inverse)"
                          : "var(--text-secondary)",
                      borderColor:
                        t === execTicker
                          ? "var(--text-primary)"
                          : "var(--border-default)",
                      padding: "5px 10px",
                      fontSize: "11px",
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="stat-label" style={{ marginBottom: "6px" }}>
                Total Shares
              </div>
              <input
                className="input"
                value={totalShares}
                onChange={(e) => setTotalShares(e.target.value)}
                style={{ width: "120px" }}
              />
            </div>
            <div />
          </div>

          <div className="stat-label" style={{ marginBottom: "6px" }}>
            Algorithm
          </div>
          <div
            style={{
              display: "flex",
              gap: "6px",
              marginBottom: "16px",
              flexWrap: "wrap",
            }}
          >
            {EXEC_ALGOS.map((a) => (
              <button
                key={a.id}
                onClick={() => setExecAlgo(a.id)}
                className="btn"
                style={{
                  background:
                    a.id === execAlgo ? "var(--text-primary)" : "transparent",
                  color:
                    a.id === execAlgo
                      ? "var(--text-inverse)"
                      : "var(--text-secondary)",
                  borderColor:
                    a.id === execAlgo
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
                <span>{a.label}</span>
                <span style={{ fontSize: "9px", opacity: 0.6 }}>{a.desc}</span>
              </button>
            ))}
          </div>

          {execAlgo === "is" && (
            <div style={{ marginBottom: "16px" }}>
              <div className="stat-label" style={{ marginBottom: "6px" }}>
                Urgency: {urgency.toFixed(2)} —{" "}
                {urgency > 0.66
                  ? "Aggressive (front-loaded)"
                  : urgency < 0.33
                    ? "Passive (back-loaded)"
                    : "Balanced"}
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={urgency}
                onChange={(e) => setUrgency(parseFloat(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>
          )}

          <button
            onClick={() => void runExecution()}
            className="btn btn-primary"
            disabled={execLoading}
          >
            {execLoading ? (
              <>
                <Spinner size={12} /> Scheduling...
              </>
            ) : (
              "Generate Schedule →"
            )}
          </button>
        </div>

        {execError && (
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
            {execError}
          </div>
        )}

        {execResult && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                gap: "12px",
                marginBottom: "20px",
              }}
            >
              <StatCard
                label="Algorithm"
                value={execResult.algorithm}
                delay={0}
              />
              <StatCard
                label="Total Shares"
                value={execResult.total_shares.toLocaleString()}
                delay={60}
              />
              <StatCard
                label="Intervals"
                value={String(execResult.n_intervals)}
                delay={120}
              />
              <StatCard
                label="Avg Participation"
                value={`${(execResult.participation_rate * 100).toFixed(2)}%`}
                sub="of market volume"
                delay={180}
              />
              <StatCard
                label="Completion"
                value={execResult.expected_completion}
                delay={240}
              />
            </div>

            <div className="card animate-fade-up" style={{ padding: "24px" }}>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  letterSpacing: "0.1em",
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                  marginBottom: "16px",
                }}
              >
                Share Distribution by Interval
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={chartData}
                  margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="interval"
                    tick={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 9,
                      fill: "var(--text-tertiary)",
                    }}
                    axisLine={false}
                    tickLine={false}
                    interval={Math.ceil(chartData.length / 8)}
                  />
                  <YAxis
                    tickFormatter={(v: number) => v.toLocaleString()}
                    tick={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      fill: "var(--text-tertiary)",
                    }}
                    axisLine={false}
                    tickLine={false}
                    width={50}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-default)",
                      borderRadius: "var(--radius-md)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                    }}
                    formatter={(v: number) => [
                      `${v.toLocaleString()} shares`,
                      "",
                    ]}
                  />
                  <ReferenceLine
                    y={execResult.total_shares / execResult.n_intervals}
                    stroke="var(--border-strong)"
                    strokeDasharray="3 3"
                  />
                  <Bar dataKey="shares" radius={[3, 3, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill="var(--accent-blue)" opacity={0.75} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {!factorResult && !execResult && !factorLoading && !execLoading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "40px 0",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "32px",
                color: "var(--text-tertiary)",
                marginBottom: "8px",
              }}
            >
              ◇
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--text-tertiary)",
              }}
            >
              Run a factor model or generate an execution schedule above
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
