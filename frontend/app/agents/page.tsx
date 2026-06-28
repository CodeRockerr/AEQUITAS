"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  extendedAgentsApi,
  type NewsSentimentResponse,
  type EarningsAnalysisResponse,
  type PortfolioConstructionResponse,
} from "@/lib/api";

const TICKERS = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA"];
const TABS = [
  { id: "news", label: "News Sentiment" },
  { id: "earnings", label: "Earnings Analysis" },
  { id: "portfolio", label: "Portfolio Construction" },
] as const;

export default function AgentsPage() {
  const [activeTab, setActiveTab] =
    useState<(typeof TABS)[number]["id"]>("news");

  // ── News sentiment state ────────────────────────────────────
  const [newsTicker, setNewsTicker] = useState("AAPL");
  const [newsResult, setNewsResult] = useState<NewsSentimentResponse | null>(
    null,
  );
  const [newsLoading, setNewsLoading] = useState(false);
  const [newsError, setNewsError] = useState<string | null>(null);

  // ── Earnings state ──────────────────────────────────────────
  const [earningsTicker, setEarningsTicker] = useState("AAPL");
  const [earningsResult, setEarningsResult] =
    useState<EarningsAnalysisResponse | null>(null);
  const [earningsLoading, setEarningsLoading] = useState(false);
  const [earningsError, setEarningsError] = useState<string | null>(null);

  // ── Portfolio state ─────────────────────────────────────────
  const [portfolioInput, setPortfolioInput] = useState("AAPL, MSFT, NVDA");
  const [portfolioResult, setPortfolioResult] =
    useState<PortfolioConstructionResponse | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  async function runNewsSentiment() {
    setNewsLoading(true);
    setNewsError(null);
    try {
      const r = await extendedAgentsApi.newsSentiment(newsTicker);
      setNewsResult(r);
    } catch (e) {
      setNewsError(
        e instanceof Error ? e.message : "News sentiment agent failed",
      );
    } finally {
      setNewsLoading(false);
    }
  }

  async function runEarnings() {
    setEarningsLoading(true);
    setEarningsError(null);
    try {
      const r = await extendedAgentsApi.earnings(earningsTicker);
      setEarningsResult(r);
    } catch (e) {
      setEarningsError(
        e instanceof Error ? e.message : "Earnings agent failed",
      );
    } finally {
      setEarningsLoading(false);
    }
  }

  async function runPortfolio() {
    setPortfolioLoading(true);
    setPortfolioError(null);
    const tickers = portfolioInput
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    if (tickers.length < 2) {
      setPortfolioError("Enter at least 2 tickers, comma-separated");
      setPortfolioLoading(false);
      return;
    }
    try {
      const r = await extendedAgentsApi.portfolio(tickers);
      setPortfolioResult(r);
    } catch (e) {
      setPortfolioError(
        e instanceof Error ? e.message : "Portfolio agent failed",
      );
    } finally {
      setPortfolioLoading(false);
    }
  }

  const sentimentVariant = (
    s: string,
  ): "green" | "red" | "amber" | "neutral" =>
    s === "bullish" ? "green" : s === "bearish" ? "red" : "amber";

  const guidanceVariant = (g: string): "green" | "red" | "amber" | "neutral" =>
    g === "positive"
      ? "green"
      : g === "negative"
        ? "red"
        : g === "mixed"
          ? "amber"
          : "neutral";

  return (
    <div style={{ minHeight: "100vh" }}>
      <PageHeader
        title="Agents"
        subtitle="NEWS SENTIMENT · EARNINGS ANALYSIS · PORTFOLIO CONSTRUCTION"
        serif
      />

      <div style={{ padding: "32px 40px" }}>
        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: "2px",
            borderBottom: "1px solid var(--border-subtle)",
            marginBottom: "24px",
          }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
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

        {/* ── News Sentiment Tab ─────────────────────────────── */}
        {activeTab === "news" && (
          <>
            <div
              className="card"
              style={{ padding: "20px 24px", marginBottom: "24px" }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr auto",
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
                        onClick={() => setNewsTicker(t)}
                        className="btn"
                        style={{
                          background:
                            t === newsTicker
                              ? "var(--text-primary)"
                              : "transparent",
                          color:
                            t === newsTicker
                              ? "var(--text-inverse)"
                              : "var(--text-secondary)",
                          borderColor:
                            t === newsTicker
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
                <button
                  onClick={() => void runNewsSentiment()}
                  className="btn btn-primary"
                  disabled={newsLoading}
                >
                  {newsLoading ? (
                    <>
                      <Spinner size={12} /> Analysing...
                    </>
                  ) : (
                    "Analyse Sentiment →"
                  )}
                </button>
              </div>
            </div>

            {newsError && (
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
                {newsError}
              </div>
            )}

            {newsResult && (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(150px, 1fr))",
                    gap: "12px",
                    marginBottom: "20px",
                  }}
                >
                  <StatCard
                    label="Sentiment"
                    value={newsResult.sentiment.toUpperCase()}
                    accent={sentimentVariant(newsResult.sentiment)}
                    delay={0}
                  />
                  <StatCard
                    label="Score"
                    value={newsResult.sentiment_score.toFixed(2)}
                    delay={60}
                  />
                  <StatCard
                    label="Trend"
                    value={newsResult.trend}
                    delay={120}
                    accent={
                      newsResult.trend === "improving"
                        ? "green"
                        : newsResult.trend === "worsening"
                          ? "red"
                          : "neutral"
                    }
                  />
                  <StatCard
                    label="Confidence"
                    value={`${(newsResult.confidence * 100).toFixed(0)}%`}
                    delay={180}
                  />
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 280px",
                    gap: "16px",
                  }}
                >
                  <div
                    className="card animate-fade-in"
                    style={{ padding: "28px" }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--font-serif)",
                        fontSize: "18px",
                        color: "var(--text-primary)",
                        marginBottom: "16px",
                      }}
                    >
                      {newsResult.ticker} — News Sentiment Summary
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: "14px",
                        color: "var(--text-secondary)",
                        lineHeight: "1.8",
                      }}
                    >
                      {newsResult.summary}
                    </div>
                    {newsResult.key_themes.length > 0 && (
                      <div
                        style={{
                          display: "flex",
                          gap: "6px",
                          marginTop: "16px",
                          flexWrap: "wrap",
                        }}
                      >
                        {newsResult.key_themes.map((theme, i) => (
                          <span
                            key={i}
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "11px",
                              padding: "4px 10px",
                              background: "var(--bg-elevated)",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: "100px",
                              color: "var(--text-secondary)",
                            }}
                          >
                            {theme}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

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
                        marginBottom: "12px",
                      }}
                    >
                      Recent Headlines
                    </div>
                    {newsResult.recent_articles.slice(0, 6).map((a, i) => (
                      <a
                        key={i}
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: "block",
                          textDecoration: "none",
                          padding: "8px 0",
                          borderBottom:
                            i < 5 ? "1px solid var(--border-subtle)" : "none",
                        }}
                      >
                        <div
                          style={{
                            fontFamily: "var(--font-sans)",
                            fontSize: "12px",
                            color: "var(--text-primary)",
                            lineHeight: "1.4",
                            marginBottom: "2px",
                          }}
                        >
                          {a.headline}
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: "var(--text-tertiary)",
                          }}
                        >
                          {a.source}
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              </>
            )}

            {!newsResult && !newsLoading && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  padding: "60px 0",
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
                  ◐
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-tertiary)",
                  }}
                >
                  Select a ticker and analyse recent news sentiment
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Earnings Analysis Tab ──────────────────────────── */}
        {activeTab === "earnings" && (
          <>
            <div
              className="card"
              style={{ padding: "20px 24px", marginBottom: "24px" }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr auto",
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
                        onClick={() => setEarningsTicker(t)}
                        className="btn"
                        style={{
                          background:
                            t === earningsTicker
                              ? "var(--text-primary)"
                              : "transparent",
                          color:
                            t === earningsTicker
                              ? "var(--text-inverse)"
                              : "var(--text-secondary)",
                          borderColor:
                            t === earningsTicker
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
                <button
                  onClick={() => void runEarnings()}
                  className="btn btn-primary"
                  disabled={earningsLoading}
                >
                  {earningsLoading ? (
                    <>
                      <Spinner size={12} /> Analysing...
                    </>
                  ) : (
                    "Analyse Earnings →"
                  )}
                </button>
              </div>
            </div>

            {earningsError && (
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
                {earningsError}
              </div>
            )}

            {earningsResult && (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(160px, 1fr))",
                    gap: "12px",
                    marginBottom: "20px",
                  }}
                >
                  <StatCard
                    label="Next Earnings"
                    value={earningsResult.next_earnings_date ?? "Not scheduled"}
                    delay={0}
                  />
                  {earningsResult.last_earnings_beat !== null && (
                    <StatCard
                      label="Last Beat"
                      value={
                        earningsResult.last_earnings_beat ? "Beat" : "Missed"
                      }
                      accent={
                        earningsResult.last_earnings_beat ? "green" : "red"
                      }
                      delay={60}
                    />
                  )}
                  {earningsResult.last_eps_surprise_pct !== null && (
                    <StatCard
                      label="EPS Surprise"
                      value={`${earningsResult.last_eps_surprise_pct >= 0 ? "+" : ""}${earningsResult.last_eps_surprise_pct}%`}
                      delay={120}
                    />
                  )}
                  <StatCard
                    label="Guidance"
                    value={earningsResult.guidance_sentiment.toUpperCase()}
                    accent={guidanceVariant(earningsResult.guidance_sentiment)}
                    delay={180}
                  />
                </div>

                {!earningsResult.history_available && (
                  <div
                    style={{
                      background: "var(--accent-amber-bg)",
                      border:
                        "1px solid color-mix(in srgb, var(--accent-amber) 30%, transparent)",
                      borderRadius: "var(--radius-md)",
                      padding: "10px 16px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--accent-amber)",
                      marginBottom: "20px",
                    }}
                  >
                    No historical EPS beat/miss data available from Finnhub for
                    this ticker — analysis below is grounded in recent news and
                    fundamentals instead.
                  </div>
                )}

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 280px",
                    gap: "16px",
                  }}
                >
                  <div
                    className="card animate-fade-in"
                    style={{ padding: "28px" }}
                  >
                    <div
                      style={{
                        fontFamily: "var(--font-serif)",
                        fontSize: "18px",
                        color: "var(--text-primary)",
                        marginBottom: "16px",
                      }}
                    >
                      {earningsResult.ticker} — Earnings Analysis
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
                      {earningsResult.analysis}
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "12px",
                    }}
                  >
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
                        Key Fundamentals
                      </div>
                      {Object.entries(earningsResult.key_metrics)
                        .filter(([, v]) => v !== null)
                        .map(([key, val]) => (
                          <div
                            key={key}
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              padding: "6px 0",
                              borderBottom: "1px solid var(--border-subtle)",
                            }}
                          >
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "11px",
                                color: "var(--text-tertiary)",
                              }}
                            >
                              {key.replace(/_/g, " ")}
                            </span>
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "11px",
                                color: "var(--text-primary)",
                              }}
                            >
                              {val}
                            </span>
                          </div>
                        ))}
                    </div>

                    {earningsResult.earnings_history.length > 0 && (
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
                          Earnings History
                        </div>
                        {earningsResult.earnings_history.map((h, i) => (
                          <div
                            key={i}
                            style={{
                              padding: "6px 0",
                              borderBottom:
                                i < earningsResult.earnings_history.length - 1
                                  ? "1px solid var(--border-subtle)"
                                  : "none",
                            }}
                          >
                            <div
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "11px",
                                color: "var(--text-primary)",
                              }}
                            >
                              {h.quarter}
                            </div>
                            <div
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "10px",
                                color: "var(--text-tertiary)",
                              }}
                            >
                              EPS {h.eps_actual} vs est. {h.eps_estimate}
                              {h.eps_surprise_pct !== null && (
                                <span
                                  style={{
                                    color:
                                      h.eps_surprise_pct >= 0
                                        ? "var(--accent-green)"
                                        : "var(--accent-red)",
                                  }}
                                >
                                  {" "}
                                  ({h.eps_surprise_pct >= 0 ? "+" : ""}
                                  {h.eps_surprise_pct}%)
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {!earningsResult && !earningsLoading && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  padding: "60px 0",
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
                  ◑
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-tertiary)",
                  }}
                >
                  Select a ticker and analyse earnings
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Portfolio Construction Tab ─────────────────────── */}
        {activeTab === "portfolio" && (
          <>
            <div
              className="card"
              style={{ padding: "20px 24px", marginBottom: "24px" }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  gap: "16px",
                  alignItems: "end",
                }}
              >
                <div>
                  <div className="stat-label" style={{ marginBottom: "6px" }}>
                    Tickers (comma-separated, 2-10)
                  </div>
                  <input
                    className="input"
                    value={portfolioInput}
                    onChange={(e) => setPortfolioInput(e.target.value)}
                    placeholder="AAPL, MSFT, NVDA"
                  />
                </div>
                <button
                  onClick={() => void runPortfolio()}
                  className="btn btn-primary"
                  disabled={portfolioLoading}
                >
                  {portfolioLoading ? (
                    <>
                      <Spinner size={12} /> Constructing...
                    </>
                  ) : (
                    "Construct Portfolio →"
                  )}
                </button>
              </div>
            </div>

            {portfolioError && (
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
                {portfolioError}
              </div>
            )}

            {portfolioResult && (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(150px, 1fr))",
                    gap: "12px",
                    marginBottom: "20px",
                  }}
                >
                  <StatCard
                    label="Max-Sharpe Return"
                    value={`${(portfolioResult.max_sharpe_return * 100).toFixed(1)}%`}
                    accent="green"
                    delay={0}
                  />
                  <StatCard
                    label="Max-Sharpe Vol"
                    value={`${(portfolioResult.max_sharpe_vol * 100).toFixed(1)}%`}
                    delay={60}
                  />
                  <StatCard
                    label="Sharpe Ratio"
                    value={portfolioResult.max_sharpe_ratio.toFixed(2)}
                    delay={120}
                  />
                  <StatCard
                    label="Min-Variance Vol"
                    value={`${(portfolioResult.min_variance_vol * 100).toFixed(1)}%`}
                    accent="blue"
                    delay={180}
                  />
                  <StatCard
                    label="Cointegrated Pairs"
                    value={String(portfolioResult.cointegrated_pairs.length)}
                    delay={240}
                  />
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "16px",
                    marginBottom: "16px",
                  }}
                >
                  <div
                    className="card animate-fade-up"
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
                      Allocation Weights
                    </div>
                    {portfolioResult.allocations.map((a, i) => (
                      <div
                        key={a.ticker}
                        style={{
                          padding: "10px 0",
                          borderBottom:
                            i < portfolioResult.allocations.length - 1
                              ? "1px solid var(--border-subtle)"
                              : "none",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: "6px",
                          }}
                        >
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "12px",
                              color: "var(--text-primary)",
                              fontWeight: 500,
                            }}
                          >
                            {a.ticker}
                          </span>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "11px",
                              color: "var(--text-tertiary)",
                            }}
                          >
                            Sharpe {(a.max_sharpe_weight * 100).toFixed(1)}% ·
                            MinVar {(a.min_variance_weight * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div style={{ display: "flex", gap: "4px" }}>
                          <div
                            style={{
                              flex: 1,
                              height: "6px",
                              background: "var(--border-subtle)",
                              borderRadius: "3px",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                height: "100%",
                                width: `${a.max_sharpe_weight * 100}%`,
                                background: "var(--accent-green)",
                                opacity: 0.8,
                              }}
                            />
                          </div>
                          <div
                            style={{
                              flex: 1,
                              height: "6px",
                              background: "var(--border-subtle)",
                              borderRadius: "3px",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                height: "100%",
                                width: `${a.min_variance_weight * 100}%`,
                                background: "var(--accent-blue)",
                                opacity: 0.8,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                    <div
                      style={{
                        display: "flex",
                        gap: "16px",
                        marginTop: "12px",
                      }}
                    >
                      <div
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
                            background: "var(--accent-green)",
                            opacity: 0.8,
                          }}
                        />
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: "var(--text-tertiary)",
                          }}
                        >
                          Max-Sharpe
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
                            width: "8px",
                            height: "8px",
                            borderRadius: "2px",
                            background: "var(--accent-blue)",
                            opacity: 0.8,
                          }}
                        />
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: "var(--text-tertiary)",
                          }}
                        >
                          Min-Variance
                        </span>
                      </div>
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
                      Cointegrated Pairs
                    </div>
                    {portfolioResult.cointegrated_pairs.length > 0 ? (
                      portfolioResult.cointegrated_pairs.map((p, i) => (
                        <div
                          key={i}
                          style={{
                            padding: "10px 0",
                            borderBottom:
                              i < portfolioResult.cointegrated_pairs.length - 1
                                ? "1px solid var(--border-subtle)"
                                : "none",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                            }}
                          >
                            <span
                              style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: "12px",
                                color: "var(--text-primary)",
                              }}
                            >
                              {p.ticker_a} / {p.ticker_b}
                            </span>
                            <Badge variant="blue">
                              p={p.p_value.toFixed(4)}
                            </Badge>
                          </div>
                          <div
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontSize: "10px",
                              color: "var(--text-tertiary)",
                              marginTop: "2px",
                            }}
                          >
                            Half-life: {p.half_life.toFixed(1)} days
                          </div>
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
                        No statistically significant cointegrated pairs found
                        among these tickers.
                      </div>
                    )}
                  </div>
                </div>

                <div
                  className="card animate-fade-up anim-delay-2"
                  style={{ padding: "28px" }}
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
                    Portfolio Thesis
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
                    {portfolioResult.thesis}
                  </div>
                </div>

                {portfolioResult.errors.length > 0 && (
                  <div
                    style={{
                      marginTop: "16px",
                      padding: "12px 16px",
                      background: "var(--accent-amber-bg)",
                      borderRadius: "var(--radius-md)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--accent-amber)",
                    }}
                  >
                    {portfolioResult.errors.map((e, i) => (
                      <div key={i}>— {e}</div>
                    ))}
                  </div>
                )}
              </>
            )}

            {!portfolioResult && !portfolioLoading && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  padding: "60px 0",
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
                  ◒
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-tertiary)",
                  }}
                >
                  Enter 2-10 tickers and construct an optimised portfolio
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
