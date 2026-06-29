"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { AgentProgress } from "@/components/ui/AgentProgress";
import { InsightStrip } from "@/components/ui/InsightStrip";
import { agentsApi, type ResearchResponse } from "@/lib/api";

const TICKERS = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA", "AMZN"];

export default function ThesesPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"thesis" | "critique" | "quant">(
    "thesis",
  );

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const r = await agentsApi.research(ticker);
      setResult(r);
      setActiveTab("thesis");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent pipeline failed");
    } finally {
      setLoading(false);
    }
  }

  const sentimentVariant = (
    s: string,
  ): "green" | "red" | "amber" | "neutral" =>
    s === "bullish" ? "green" : s === "bearish" ? "red" : "amber";

  // Derive a real, data-driven Observed/Why/Next summary rather than
  // static text — this surfaces the same kind of contradiction the
  // critic agent itself checks for, visually, before the prose wall.
  function buildInsight(r: ResearchResponse) {
    const noticed = `${
      r.thesis_sentiment === "bullish"
        ? "Bullish"
        : r.thesis_sentiment === "bearish"
          ? "Bearish"
          : "Mixed"
    } thesis on ${r.ticker} — regime is ${r.current_regime}, momentum score ${r.signal_score.toFixed(2)}`;

    let whyItMatters: string;
    const regimeBullish = r.current_regime === "Bull";
    const regimeBearish = r.current_regime === "Bear";
    if (r.signal_score > 0.2 && regimeBearish) {
      whyItMatters =
        "Bullish momentum contradicts a Bear regime — worth scrutiny before acting.";
    } else if (r.signal_score < -0.2 && regimeBullish) {
      whyItMatters =
        "Bearish momentum contradicts a Bull regime — worth scrutiny before acting.";
    } else if (r.revision_count > 1) {
      whyItMatters =
        "The critic requested a revision before approving this thesis.";
    } else {
      whyItMatters =
        "Signals and regime are directionally aligned with the thesis.";
    }

    const nextAction =
      r.confidence_score > 0.7
        ? "High confidence — review the full Bull/Bear case below."
        : "Moderate confidence — cross-check the Quant Evidence tab before acting.";

    return { noticed, whyItMatters, nextAction };
  }

  return (
    <div style={{ minHeight: "100vh" }}>
      <PageHeader
        title="Trade Theses"
        subtitle="AI-GENERATED INVESTMENT RESEARCH"
        serif
      >
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <select
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            className="input"
            style={{ width: "120px" }}
          >
            {TICKERS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button
            onClick={() => void generate()}
            className="btn btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <Spinner size={12} /> Researching...
              </>
            ) : (
              "Generate Thesis →"
            )}
          </button>
        </div>
      </PageHeader>

      <div style={{ padding: "32px 40px" }}>
        {loading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "60px 0",
              gap: "16px",
            }}
          >
            <Spinner size={24} />
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-tertiary)",
              }}
            >
              Running 4-node agent pipeline...
            </div>
            <AgentProgress
              steps={[
                "Research node: fetching company data",
                "Quant node: computing signals & regime",
                "Thesis node: generating investment thesis",
                "Critic node: evaluating thesis quality",
              ]}
              msPerStep={5000}
            />
          </div>
        )}

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

        {result && !loading && (
          <>
            {/* Header stats */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                gap: "12px",
                marginBottom: "24px",
              }}
            >
              <StatCard
                label="Sentiment"
                value={result.thesis_sentiment.toUpperCase()}
                accent={sentimentVariant(result.thesis_sentiment)}
                delay={0}
              />
              <StatCard
                label="Confidence"
                value={`${(result.confidence_score * 100).toFixed(0)}%`}
                delay={60}
              />
              <StatCard
                label="Regime"
                value={result.current_regime}
                accent={
                  result.current_regime === "Bull"
                    ? "green"
                    : result.current_regime === "Bear"
                      ? "red"
                      : "amber"
                }
                delay={120}
              />
              <StatCard
                label="ML Forecast"
                value={result.predicted_return_pct}
                accent={
                  result.predicted_return_pct.startsWith("+") ? "green" : "red"
                }
                delay={180}
              />
              <StatCard
                label="VaR 95%"
                value={`$${result.var_95.toLocaleString()}`}
                sub="per $100k"
                delay={240}
              />
              <StatCard
                label="Revisions"
                value={String(result.revision_count)}
                sub="Critic loops"
                delay={300}
              />
            </div>

            {/* Insight strip — Observed / Why it matters / Next action */}
            <InsightStrip {...buildInsight(result)} />

            {/* Tabs */}
            <div
              style={{
                display: "flex",
                gap: "2px",
                borderBottom: "1px solid var(--border-subtle)",
                marginBottom: "24px",
              }}
            >
              {[
                { id: "thesis", label: "Investment Thesis" },
                { id: "critique", label: "Critic Review" },
                { id: "quant", label: "Quant Evidence" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "12px",
                    padding: "10px 16px",
                    background: "none",
                    border: "none",
                    borderBottom:
                      activeTab === tab.id
                        ? "2px solid var(--text-primary)"
                        : "2px solid transparent",
                    color:
                      activeTab === tab.id
                        ? "var(--text-primary)"
                        : "var(--text-tertiary)",
                    cursor: "pointer",
                    letterSpacing: "0.04em",
                    marginBottom: "-1px",
                    transition: "all var(--duration-fast)",
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Thesis tab */}
            {activeTab === "thesis" && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 280px",
                  gap: "16px",
                }}
              >
                <div
                  className="card animate-fade-in"
                  style={{ padding: "32px" }}
                >
                  <div
                    style={{
                      fontFamily: "var(--font-serif)",
                      fontSize: "20px",
                      color: "var(--text-primary)",
                      marginBottom: "24px",
                      letterSpacing: "-0.01em",
                    }}
                  >
                    {ticker} — Investment Thesis
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-sans)",
                      fontSize: "14px",
                      color: "var(--text-secondary)",
                      lineHeight: "1.8",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {result.final_thesis}
                  </div>
                </div>

                {/* Sidebar */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                  }}
                >
                  {/* Citations */}
                  <div
                    className="card animate-fade-in"
                    style={{ padding: "16px 20px" }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "10px",
                        letterSpacing: "0.1em",
                        color: "var(--text-tertiary)",
                        textTransform: "uppercase",
                        marginBottom: "10px",
                      }}
                    >
                      Sources
                    </div>
                    {result.filing_citations.length > 0 ? (
                      result.filing_citations.map((c, i) => (
                        <div
                          key={i}
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "var(--text-secondary)",
                            padding: "6px 0",
                            borderBottom:
                              i < result.filing_citations.length - 1
                                ? "1px solid var(--border-subtle)"
                                : "none",
                          }}
                        >
                          [{i + 1}] {c}
                        </div>
                      ))
                    ) : (
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "11px",
                          color: "var(--text-tertiary)",
                        }}
                      >
                        No filing documents ingested
                      </div>
                    )}
                  </div>

                  {/* SHAP */}
                  {result.top_shap_drivers.length > 0 && (
                    <div
                      className="card animate-fade-in"
                      style={{ padding: "16px 20px" }}
                    >
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          letterSpacing: "0.1em",
                          color: "var(--text-tertiary)",
                          textTransform: "uppercase",
                          marginBottom: "10px",
                        }}
                      >
                        Top Signals
                      </div>
                      {result.top_shap_drivers.slice(0, 3).map((d, i) => (
                        <div
                          key={i}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            padding: "6px 0",
                            borderBottom:
                              i < 2 ? "1px solid var(--border-subtle)" : "none",
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "11px",
                              color: "var(--text-secondary)",
                            }}
                          >
                            {d.feature}
                          </span>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "11px",
                              color:
                                d.shap_value >= 0
                                  ? "var(--accent-green)"
                                  : "var(--accent-red)",
                            }}
                          >
                            {d.shap_value >= 0 ? "+" : ""}
                            {d.shap_value.toFixed(4)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Errors */}
                  {result.errors.length > 0 && (
                    <div
                      className="card"
                      style={{
                        padding: "16px 20px",
                        background: "var(--accent-amber-bg)",
                      }}
                    >
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          color: "var(--accent-amber)",
                          textTransform: "uppercase",
                          letterSpacing: "0.1em",
                          marginBottom: "8px",
                        }}
                      >
                        Warnings
                      </div>
                      {result.errors.map((e, i) => (
                        <div
                          key={i}
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: "var(--accent-amber)",
                            lineHeight: "1.6",
                          }}
                        >
                          — {e}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Critique tab */}
            {activeTab === "critique" && (
              <div
                className="card animate-fade-in"
                style={{ padding: "32px", maxWidth: "720px" }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    letterSpacing: "0.1em",
                    color: "var(--text-tertiary)",
                    textTransform: "uppercase",
                    marginBottom: "16px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <span>Critic Agent Review</span>
                  <Badge
                    variant={result.revision_count > 1 ? "amber" : "green"}
                  >
                    {result.revision_count} revision
                    {result.revision_count !== 1 ? "s" : ""}
                  </Badge>
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "14px",
                    color: "var(--text-secondary)",
                    lineHeight: "1.8",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {result.critique}
                </div>
              </div>
            )}

            {/* Quant evidence tab */}
            {activeTab === "quant" && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                  maxWidth: "720px",
                }}
              >
                <div
                  className="card animate-fade-in"
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
                    Quantitative Signals
                  </div>
                  {[
                    {
                      label: "Regime",
                      value: result.current_regime,
                      sub: `${(result.regime_confidence * 100).toFixed(0)}% confidence`,
                    },
                    {
                      label: "Direction",
                      value: result.signal_direction.toUpperCase(),
                      sub: `Score: ${result.signal_score.toFixed(3)}`,
                    },
                    {
                      label: "ML Forecast",
                      value: result.predicted_return_pct,
                      sub: "Next-day return",
                    },
                    {
                      label: "VaR 95%",
                      value: `$${result.var_95.toLocaleString()}`,
                      sub: "Per $100k position",
                    },
                  ].map(({ label, value, sub }) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        padding: "10px 0",
                        borderBottom: "1px solid var(--border-subtle)",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: "var(--text-tertiary)",
                            textTransform: "uppercase",
                            letterSpacing: "0.06em",
                          }}
                        >
                          {label}
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "var(--text-tertiary)",
                            marginTop: "2px",
                          }}
                        >
                          {sub}
                        </div>
                      </div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "14px",
                          color: "var(--text-primary)",
                          fontWeight: "500",
                        }}
                      >
                        {value}
                      </div>
                    </div>
                  ))}
                </div>

                <div
                  className="card animate-fade-in anim-delay-1"
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
                    SHAP Feature Attribution
                  </div>
                  {result.top_shap_drivers.map((d, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 0",
                        borderBottom:
                          i < result.top_shap_drivers.length - 1
                            ? "1px solid var(--border-subtle)"
                            : "none",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: "4px",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color: "var(--text-primary)",
                          }}
                        >
                          {d.feature}
                        </span>
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "11px",
                            color:
                              d.shap_value >= 0
                                ? "var(--accent-green)"
                                : "var(--accent-red)",
                          }}
                        >
                          {d.shap_value >= 0 ? "+" : ""}
                          {d.shap_value.toFixed(4)}
                        </span>
                      </div>
                      <div
                        style={{
                          height: "3px",
                          background: "var(--border-subtle)",
                          borderRadius: "2px",
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            height: "100%",
                            width: `${(d.magnitude / result.top_shap_drivers[0].magnitude) * 100}%`,
                            background:
                              d.shap_value >= 0
                                ? "var(--accent-green)"
                                : "var(--accent-red)",
                            borderRadius: "2px",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {!result && !loading && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "80px 0",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "40px",
                color: "var(--text-tertiary)",
                marginBottom: "12px",
              }}
            >
              ◧
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-tertiary)",
                letterSpacing: "0.06em",
              }}
            >
              Select a ticker and generate an AI-powered investment thesis
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
