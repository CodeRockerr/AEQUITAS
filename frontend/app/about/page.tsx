"use client";

import Link from "next/link";

const TECH_STACK = [
  {
    layer: "Agent Orchestration",
    items: ["LangGraph 0.2", "Groq LLM (llama-3.3-70b)", "pgvector RAG"],
  },
  {
    layer: "ML & Algorithms",
    items: ["XGBoost + SHAP", "HMM Regime Detector", "Black-Scholes + Greeks"],
  },
  {
    layer: "Risk & Portfolio",
    items: ["VaR / CVaR", "Monte Carlo", "Mean-Variance Optimiser"],
  },
  {
    layer: "Signals",
    items: ["RSI / MACD / Bollinger", "Pairs Trading", "Kalman Filter"],
  },
  {
    layer: "Data Pipeline",
    items: ["yFinance", "EDGAR API", "TimescaleDB Hypertables"],
  },
  {
    layer: "Backend",
    items: ["FastAPI", "SQLAlchemy Async", "Alembic Migrations"],
  },
  { layer: "Frontend", items: ["Next.js 14", "TypeScript", "Recharts"] },
  {
    layer: "Infrastructure",
    items: ["Docker Compose", "GitHub Actions CI/CD", "Railway + Vercel"],
  },
];

const PIPELINE = [
  {
    step: "01",
    title: "Data Ingestion",
    desc: "Real-time OHLCV price data from Yahoo Finance and SEC filings ingested into TimescaleDB hypertables.",
  },
  {
    step: "02",
    title: "Quantitative Signals",
    desc: "Momentum signals (RSI, MACD, Bollinger), pairs trading with Kalman filter hedge ratios, and regime detection via HMM.",
  },
  {
    step: "03",
    title: "ML Forecasting",
    desc: "XGBoost return forecaster trained with TimeSeriesSplit cross-validation. SHAP values explain every prediction.",
  },
  {
    step: "04",
    title: "Risk Engine",
    desc: "VaR and CVaR via three methods (historical, parametric, Monte Carlo). Black-Scholes pricer with full Greeks engine.",
  },
  {
    step: "05",
    title: "Research Agent",
    desc: "LangGraph 4-node pipeline: research → quant → thesis generation → critic revision loop.",
  },
  {
    step: "06",
    title: "Trade Thesis",
    desc: "Structured investment thesis grounded in real filings, quantitative signals, and ML evidence — with citations.",
  },
];

const METRICS = [
  { value: "87", label: "Unit Tests" },
  { value: "12", label: "Algorithms" },
  { value: "4", label: "Agent Nodes" },
  { value: "6", label: "API Routers" },
];

export default function AboutPage() {
  return (
    <div style={{ minHeight: "100vh" }}>
      {/* ── Hero ──────────────────────────────────────────── */}
      <div
        style={{
          padding: "80px 40px 72px",
          borderBottom: "1px solid var(--border-subtle)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Grid background */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            backgroundImage:
              "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            opacity: 0.5,
          }}
        />

        <div style={{ position: "relative", maxWidth: "680px" }}>
          {/* Eyebrow */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "4px 12px 4px 8px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "100px",
              marginBottom: "24px",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                letterSpacing: "0.12em",
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
              }}
            >
              v0.7.0 · Open Source
            </span>
          </div>

          <h1
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(44px, 7vw, 72px)",
              fontWeight: "400",
              lineHeight: "1.02",
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              marginBottom: "24px",
            }}
          >
            Quant research,
            <br />
            <em style={{ color: "var(--text-secondary)" }}>reimagined.</em>
          </h1>

          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "17px",
              color: "var(--text-secondary)",
              lineHeight: "1.75",
              maxWidth: "520px",
              marginBottom: "40px",
            }}
          >
            AEQUITAS is a full-stack agentic quantitative research platform that
            combines financial algorithms, ML models, and LLM reasoning to
            generate institutional-grade investment theses — automatically.
          </p>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <Link
              href="/dashboard"
              className="btn btn-primary"
              style={{ fontSize: "13px", padding: "10px 20px" }}
            >
              Open Dashboard →
            </Link>
            <a
              href="https://github.com/CodeRockerr/AEQUITAS"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost"
              style={{ fontSize: "13px", padding: "10px 20px" }}
            >
              View on GitHub
            </a>
          </div>
        </div>
      </div>

      {/* ── Metrics strip ─────────────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        {METRICS.map(({ value, label }, i) => (
          <div
            key={label}
            style={{
              padding: "28px 32px",
              borderRight:
                i < METRICS.length - 1
                  ? "1px solid var(--border-subtle)"
                  : "none",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "36px",
                fontWeight: "500",
                color: "var(--text-primary)",
                lineHeight: 1,
                marginBottom: "6px",
                letterSpacing: "-0.02em",
              }}
            >
              {value}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                letterSpacing: "0.1em",
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
              }}
            >
              {label}
            </div>
          </div>
        ))}
      </div>

      <div style={{ padding: "64px 40px", maxWidth: "1100px" }}>
        {/* ── What it does ──────────────────────────────────── */}
        <div style={{ marginBottom: "72px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.14em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              marginBottom: "20px",
            }}
          >
            What it does
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: "1px",
              background: "var(--border-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-lg)",
              overflow: "hidden",
            }}
          >
            {[
              {
                icon: "◈",
                title: "Agentic research pipeline",
                desc: "A 4-node LangGraph graph autonomously researches a company, computes quantitative signals, generates an investment thesis, and self-critiques it in a revision loop.",
              },
              {
                icon: "◫",
                title: "Real financial algorithms",
                desc: "12 production-grade algorithms: Black-Scholes + Greeks, VaR/CVaR (3 methods), mean-variance portfolio optimisation, pairs trading with Kalman filter hedge ratios.",
              },
              {
                icon: "◧",
                title: "ML with explainability",
                desc: "XGBoost return forecaster with SHAP attribution. Hidden Markov Model regime detector classifying Bull, Bear, and High-Volatility market states.",
              },
              {
                icon: "◬",
                title: "Vectorised backtesting",
                desc: "RSI, MACD, and Bollinger Band strategies backtested with full tearsheets: Sharpe, Sortino, Calmar, max drawdown, alpha vs buy-and-hold.",
              },
            ].map(({ icon, title, desc }) => (
              <div
                key={title}
                style={{
                  background: "var(--bg-surface)",
                  padding: "28px 32px",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "20px",
                    color: "var(--text-tertiary)",
                    marginBottom: "12px",
                  }}
                >
                  {icon}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "15px",
                    fontWeight: "500",
                    color: "var(--text-primary)",
                    marginBottom: "8px",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {title}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: "13px",
                    color: "var(--text-secondary)",
                    lineHeight: "1.7",
                  }}
                >
                  {desc}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Pipeline ──────────────────────────────────────── */}
        <div style={{ marginBottom: "72px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.14em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              marginBottom: "20px",
            }}
          >
            Research pipeline
          </div>

          <div style={{ position: "relative" }}>
            {/* Vertical line */}
            <div
              style={{
                position: "absolute",
                left: "19px",
                top: "8px",
                bottom: "8px",
                width: "1px",
                background: "var(--border-subtle)",
              }}
            />

            <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
              {PIPELINE.map(({ step, title, desc }, i) => (
                <div
                  key={step}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "40px 1fr",
                    gap: "20px",
                    padding: "20px 0",
                    borderBottom:
                      i < PIPELINE.length - 1
                        ? "1px solid var(--border-subtle)"
                        : "none",
                    alignItems: "start",
                  }}
                >
                  <div
                    style={{
                      width: "38px",
                      height: "38px",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--text-tertiary)",
                      letterSpacing: "0.04em",
                      flexShrink: 0,
                      position: "relative",
                      zIndex: 1,
                    }}
                  >
                    {step}
                  </div>
                  <div style={{ paddingTop: "8px" }}>
                    <div
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: "14px",
                        fontWeight: "500",
                        color: "var(--text-primary)",
                        marginBottom: "4px",
                      }}
                    >
                      {title}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: "13px",
                        color: "var(--text-secondary)",
                        lineHeight: "1.7",
                      }}
                    >
                      {desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Tech stack ────────────────────────────────────── */}
        <div style={{ marginBottom: "72px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.14em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              marginBottom: "20px",
            }}
          >
            Tech stack
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            {TECH_STACK.map(({ layer, items }) => (
              <div
                key={layer}
                className="card"
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
                  {layer}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                  {items.map((item) => (
                    <span
                      key={item}
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        padding: "3px 8px",
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "100px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Architecture diagram ──────────────────────────── */}
        <div style={{ marginBottom: "72px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.14em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              marginBottom: "20px",
            }}
          >
            Architecture
          </div>

          <div
            className="card"
            style={{ padding: "32px", fontFamily: "var(--font-mono)" }}
          >
            {[
              {
                label: "Data Layer",
                items: ["yFinance · EDGAR · TimescaleDB · pgvector"],
                color: "var(--accent-green)",
              },
              {
                label: "Agent Layer",
                items: [
                  "LangGraph · Research Agent · Quant Agent · Critic Agent",
                ],
                color: "var(--accent-blue)",
              },
              {
                label: "Algo Layer",
                items: [
                  "Signals · Pricing · Risk · Portfolio · ML Models · Backtester",
                ],
                color: "var(--accent-amber)",
              },
              {
                label: "API Layer",
                items: [
                  "FastAPI · Pydantic v2 · SQLAlchemy Async · Celery · JWT Auth",
                ],
                color: "var(--text-tertiary)",
              },
              {
                label: "Frontend",
                items: [
                  "Next.js 14 · TypeScript · Recharts · Dark/Light theme",
                ],
                color: "var(--accent-green)",
              },
            ].map(({ label, items, color }, i, arr) => (
              <div key={label}>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "120px 1fr",
                    gap: "16px",
                    alignItems: "center",
                    padding: "12px 0",
                  }}
                >
                  <div
                    style={{
                      fontSize: "10px",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      color: "var(--text-tertiary)",
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      padding: "8px 14px",
                      background: "var(--bg-elevated)",
                      borderRadius: "var(--radius-md)",
                      border: `1px solid ${color}`,
                      borderLeft: `3px solid ${color}`,
                      fontSize: "12px",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {items[0]}
                  </div>
                </div>
                {i < arr.length - 1 && (
                  <div
                    style={{
                      marginLeft: "120px",
                      paddingLeft: "16px",
                      height: "16px",
                      display: "flex",
                      alignItems: "center",
                    }}
                  >
                    <div
                      style={{
                        marginLeft: "50%",
                        width: "1px",
                        height: "100%",
                        background: "var(--border-subtle)",
                      }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Built by ──────────────────────────────────────── */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
            marginBottom: "72px",
          }}
        >
          <div className="card" style={{ padding: "28px 32px" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                letterSpacing: "0.14em",
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
                marginBottom: "16px",
              }}
            >
              Built by
            </div>
            <div
              style={{
                fontFamily: "var(--font-serif)",
                fontSize: "24px",
                color: "var(--text-primary)",
                letterSpacing: "-0.02em",
                marginBottom: "6px",
              }}
            >
              Adit Shah
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-secondary)",
                lineHeight: "1.7",
                marginBottom: "16px",
              }}
            >
              MS Computer Science · NC State University
              <br />
              GPA 3.80 · AI/ML · Software Development · Research · Quant Systems
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <a
                href="https://github.com/CodeRockerr"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost"
                style={{ fontSize: "11px", padding: "5px 12px" }}
              >
                GitHub
              </a>
              <a
                href="https://www.linkedin.com/in/shahadit0404/"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost"
                style={{ fontSize: "11px", padding: "5px 12px" }}
              >
                LinkedIn
              </a>
              <a
                href="https://adit-2d-portfolio.vercel.app/"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost"
                style={{ fontSize: "11px", padding: "5px 12px" }}
              >
                Portfolio
              </a>
              <a
                href="https://drive.google.com/file/d/16_bFetVUPBOT01t3aSIqqDIR703DT7Lc/view?usp=sharing"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-ghost"
                style={{ fontSize: "11px", padding: "5px 12px" }}
              >
                Resume
              </a>
            </div>
          </div>

          <div className="card" style={{ padding: "28px 32px" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                letterSpacing: "0.14em",
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
                marginBottom: "16px",
              }}
            >
              Project
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-secondary)",
                lineHeight: "1.9",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--border-subtle)",
                  paddingBottom: "8px",
                  marginBottom: "8px",
                }}
              >
                <span style={{ color: "var(--text-tertiary)" }}>Version</span>
                <span>v0.7.0</span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--border-subtle)",
                  paddingBottom: "8px",
                  marginBottom: "8px",
                }}
              >
                <span style={{ color: "var(--text-tertiary)" }}>License</span>
                <span>MIT</span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--border-subtle)",
                  paddingBottom: "8px",
                  marginBottom: "8px",
                }}
              >
                <span style={{ color: "var(--text-tertiary)" }}>Stack</span>
                <span>Python 3.13 · Node 20</span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--border-subtle)",
                  paddingBottom: "8px",
                  marginBottom: "8px",
                }}
              >
                <span style={{ color: "var(--text-tertiary)" }}>Tests</span>
                <span style={{ color: "var(--accent-green)" }}>87 passing</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-tertiary)" }}>CI/CD</span>
                <span style={{ color: "var(--accent-green)" }}>
                  GitHub Actions
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── CTA ───────────────────────────────────────────── */}
        <div
          style={{
            textAlign: "center",
            padding: "48px 32px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-xl)",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(24px, 4vw, 36px)",
              color: "var(--text-primary)",
              letterSpacing: "-0.02em",
              marginBottom: "12px",
            }}
          >
            Start researching.
          </div>
          <div
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "14px",
              color: "var(--text-secondary)",
              marginBottom: "28px",
              lineHeight: "1.7",
            }}
          >
            Ingest a ticker, run the agent pipeline,
            <br />
            get an institutional-grade thesis in seconds.
          </div>
          <div
            style={{
              display: "flex",
              gap: "10px",
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            <Link
              href="/dashboard"
              className="btn btn-primary"
              style={{ fontSize: "13px", padding: "10px 24px" }}
            >
              Open Dashboard →
            </Link>
            <Link
              href="/theses"
              className="btn btn-ghost"
              style={{ fontSize: "13px", padding: "10px 24px" }}
            >
              Generate a Thesis
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
