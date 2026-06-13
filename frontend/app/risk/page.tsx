"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  riskApi,
  pricingApi,
  type VaRResponse,
  type BlackScholesResponse,
} from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const TICKERS = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA"];
const METHODS = ["historical", "parametric", "montecarlo"] as const;

export default function RiskPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [portfolioValue, setPortfolioValue] = useState("100000");
  const [varResults, setVarResults] = useState<Record<string, VaRResponse>>({});
  const [loadingVar, setLoadingVar] = useState(false);

  // Options pricer state
  const [spot, setSpot] = useState("211");
  const [strike, setStrike] = useState("211");
  const [vol, setVol] = useState("0.25");
  const [expiry, setExpiry] = useState("0.25");
  const [rate, setRate] = useState("0.053");
  const [optType, setOptType] = useState<"call" | "put">("call");
  const [bsResult, setBsResult] = useState<BlackScholesResponse | null>(null);
  const [loadingBS, setLoadingBS] = useState(false);
  const [errorVar, setErrorVar] = useState<string | null>(null);
  const [errorBS, setErrorBS] = useState<string | null>(null);

  async function runVar() {
    setLoadingVar(true);
    setErrorVar(null);
    const pv = parseFloat(portfolioValue);
    try {
      const results = await Promise.all(
        METHODS.map((m) =>
          riskApi.var(ticker, pv, m).then((r) => [m, r] as const),
        ),
      );
      setVarResults(Object.fromEntries(results));
    } catch (e) {
      setErrorVar(e instanceof Error ? e.message : "VaR calculation failed");
    } finally {
      setLoadingVar(false);
    }
  }

  async function runBS() {
    setLoadingBS(true);
    setErrorBS(null);
    try {
      const r = await pricingApi.blackScholes({
        spot: parseFloat(spot),
        strike: parseFloat(strike),
        rate: parseFloat(rate),
        volatility: parseFloat(vol),
        expiry: parseFloat(expiry),
        option_type: optType,
      });
      setBsResult(r);
    } catch (e) {
      setErrorBS(e instanceof Error ? e.message : "Pricing failed");
    } finally {
      setLoadingBS(false);
    }
  }

  const varChartData = METHODS.map((m) =>
    varResults[m]
      ? {
          method: m.charAt(0).toUpperCase() + m.slice(1, 4),
          var: varResults[m].var,
          cvar: varResults[m].cvar,
        }
      : null,
  ).filter(Boolean);

  return (
    <div style={{ minHeight: "100vh" }}>
      <PageHeader title="Risk" subtitle="VAR · CVAR · OPTIONS PRICING" serif />

      <div style={{ padding: "32px 40px" }}>
        {/* ── VaR Section ───────────────────────────────── */}
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
          Value at Risk Analysis
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
                Portfolio Value
              </div>
              <input
                className="input"
                value={portfolioValue}
                onChange={(e) => setPortfolioValue(e.target.value)}
                style={{ width: "140px" }}
                placeholder="100000"
              />
            </div>
            <div />
            <button
              onClick={() => void runVar()}
              className="btn btn-primary"
              disabled={loadingVar}
            >
              {loadingVar ? (
                <>
                  <Spinner size={12} /> Computing...
                </>
              ) : (
                "Compute VaR →"
              )}
            </button>
          </div>
        </div>

        {errorVar && (
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
            {errorVar}
          </div>
        )}

        {Object.keys(varResults).length > 0 && (
          <>
            {/* Stats row */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                gap: "12px",
                marginBottom: "20px",
              }}
            >
              {METHODS.map(
                (m) =>
                  varResults[m] && (
                    <div
                      key={m}
                      className="card animate-fade-up"
                      style={{ padding: "16px 20px" }}
                    >
                      <div
                        className="stat-label"
                        style={{ marginBottom: "4px" }}
                      >
                        {m.charAt(0).toUpperCase() + m.slice(1)} VaR
                      </div>
                      <div
                        className="stat-value"
                        style={{ fontSize: "18px", color: "var(--accent-red)" }}
                      >
                        ${varResults[m].var.toLocaleString()}
                      </div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          color: "var(--text-tertiary)",
                          marginTop: "4px",
                        }}
                      >
                        CVaR: ${varResults[m].cvar.toLocaleString()}
                      </div>
                    </div>
                  ),
              )}
            </div>

            {/* Chart + interpretation */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
                marginBottom: "32px",
              }}
            >
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
                  VaR vs CVaR by Method
                </div>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={varChartData} barGap={4}>
                    <XAxis
                      dataKey="method"
                      tick={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 10,
                        fill: "var(--text-tertiary)",
                      }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tickFormatter={(v: number) => [
                        `$${v.toLocaleString()}`,
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
                      formatter={(v: number) => [`$${v.toLocaleString()}`, ""]}
                    />
                    <Bar dataKey="var" name="VaR" radius={[3, 3, 0, 0]}>
                      {varChartData.map((_, i) => (
                        <Cell key={i} fill="var(--accent-red)" opacity={0.7} />
                      ))}
                    </Bar>
                    <Bar dataKey="cvar" name="CVaR" radius={[3, 3, 0, 0]}>
                      {varChartData.map((_, i) => (
                        <Cell
                          key={i}
                          fill="var(--accent-amber)"
                          opacity={0.7}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", gap: "16px", marginTop: "8px" }}>
                  {[
                    { label: "VaR", color: "var(--accent-red)" },
                    { label: "CVaR", color: "var(--accent-amber)" },
                  ].map(({ label, color }) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <div
                        style={{
                          width: "8px",
                          height: "8px",
                          borderRadius: "2px",
                          background: color,
                          opacity: 0.7,
                        }}
                      />
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          color: "var(--text-tertiary)",
                        }}
                      >
                        {label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div
                className="card animate-fade-up anim-delay-1"
                style={{ padding: "24px" }}
              >
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
                  Interpretation
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "13px",
                    color: "var(--text-secondary)",
                    lineHeight: "1.8",
                  }}
                >
                  {varResults["historical"]?.interpretation}
                </div>
                <div
                  style={{
                    marginTop: "16px",
                    padding: "10px 12px",
                    background: "var(--bg-elevated)",
                    borderRadius: "var(--radius-md)",
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    color: "var(--text-tertiary)",
                  }}
                >
                  Confidence: 95% · Horizon: 1 day · Portfolio: $
                  {parseFloat(portfolioValue).toLocaleString()}
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── Black-Scholes Section ─────────────────────── */}
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
          Black-Scholes Options Pricer
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <div className="card" style={{ padding: "24px" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "12px",
                marginBottom: "16px",
              }}
            >
              {[
                {
                  label: "Spot Price",
                  value: spot,
                  set: setSpot,
                  placeholder: "211.00",
                },
                {
                  label: "Strike Price",
                  value: strike,
                  set: setStrike,
                  placeholder: "211.00",
                },
                {
                  label: "Volatility (σ)",
                  value: vol,
                  set: setVol,
                  placeholder: "0.25",
                },
                {
                  label: "Expiry (years)",
                  value: expiry,
                  set: setExpiry,
                  placeholder: "0.25",
                },
                {
                  label: "Risk-free Rate",
                  value: rate,
                  set: setRate,
                  placeholder: "0.053",
                },
              ].map(({ label, value, set, placeholder }) => (
                <div key={label}>
                  <div className="stat-label" style={{ marginBottom: "4px" }}>
                    {label}
                  </div>
                  <input
                    className="input"
                    value={value}
                    onChange={(e) => set(e.target.value)}
                    placeholder={placeholder}
                  />
                </div>
              ))}
              <div>
                <div className="stat-label" style={{ marginBottom: "4px" }}>
                  Option Type
                </div>
                <div style={{ display: "flex", gap: "4px" }}>
                  {(["call", "put"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setOptType(t)}
                      className="btn"
                      style={{
                        flex: 1,
                        background:
                          t === optType ? "var(--text-primary)" : "transparent",
                        color:
                          t === optType
                            ? "var(--text-inverse)"
                            : "var(--text-secondary)",
                        borderColor:
                          t === optType
                            ? "var(--text-primary)"
                            : "var(--border-default)",
                        padding: "6px 8px",
                        fontSize: "11px",
                      }}
                    >
                      {t.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={() => void runBS()}
              className="btn btn-primary"
              disabled={loadingBS}
              style={{ width: "100%" }}
            >
              {loadingBS ? (
                <>
                  <Spinner size={12} /> Pricing...
                </>
              ) : (
                "Price Option →"
              )}
            </button>

            {errorBS && (
              <div
                style={{
                  marginTop: "12px",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--accent-red)",
                }}
              >
                {errorBS}
              </div>
            )}
          </div>

          {bsResult ? (
            <div className="card animate-fade-in" style={{ padding: "24px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <div className="stat-label">Option Price</div>
                  <div
                    className="stat-value"
                    style={{ fontSize: "32px", marginTop: "4px" }}
                  >
                    ${bsResult.price.toFixed(4)}
                  </div>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  <Badge variant="neutral">
                    {bsResult.option_type.toUpperCase()}
                  </Badge>
                  <Badge
                    variant={
                      bsResult.moneyness === "ITM"
                        ? "green"
                        : bsResult.moneyness === "OTM"
                          ? "red"
                          : "amber"
                    }
                  >
                    {bsResult.moneyness}
                  </Badge>
                </div>
              </div>

              <div className="divider" style={{ marginBottom: "16px" }} />

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
                Greeks
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "8px",
                }}
              >
                {[
                  {
                    label: "Delta (Δ)",
                    value: bsResult.greeks.delta,
                    desc: "Price sensitivity",
                  },
                  {
                    label: "Gamma (Γ)",
                    value: bsResult.greeks.gamma,
                    desc: "Delta sensitivity",
                  },
                  {
                    label: "Vega (ν)",
                    value: bsResult.greeks.vega,
                    desc: "Vol sensitivity",
                  },
                  {
                    label: "Theta (Θ)",
                    value: bsResult.greeks.theta,
                    desc: "Time decay/day",
                  },
                  {
                    label: "Rho (ρ)",
                    value: bsResult.greeks.rho,
                    desc: "Rate sensitivity",
                  },
                ].map(({ label, value, desc }) => (
                  <div
                    key={label}
                    style={{
                      padding: "10px 12px",
                      background: "var(--bg-elevated)",
                      borderRadius: "var(--radius-md)",
                    }}
                  >
                    <div className="stat-label">{label}</div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "16px",
                        color: "var(--text-primary)",
                        fontWeight: "500",
                        marginTop: "2px",
                      }}
                    >
                      {value.toFixed(4)}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "9px",
                        color: "var(--text-tertiary)",
                        marginTop: "2px",
                      }}
                    >
                      {desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div
              className="card"
              style={{
                padding: "24px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
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
                ◬
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-tertiary)",
                }}
              >
                Enter parameters and price the option
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
