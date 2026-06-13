"use client";

import { useEffect, useState } from "react";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { healthApi } from "@/lib/api";

const TICKERS = [
  "AAPL",
  "MSFT",
  "SPY",
  "NVDA",
  "TSLA",
  "AMZN",
  "META",
  "GOOGL",
];

export default function HomePage() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [uptime, setUptime] = useState<string>("—");

  useEffect(() => {
    healthApi
      .check()
      .then((r) => {
        setStatus("online");
        setUptime(`${Math.round(r.uptime_seconds)}s`);
      })
      .catch(() => setStatus("offline"));
  }, []);

  const tickerDisplay = [...TICKERS, ...TICKERS].map((t, i) => (
    <span
      key={i}
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "11px",
        color: "var(--text-tertiary)",
        letterSpacing: "0.06em",
        padding: "0 24px",
      }}
    >
      {t}{" "}
      <span style={{ color: "var(--text-primary)", opacity: 0.4 }}>———</span>
    </span>
  ));

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Hero */}
      <div
        style={{
          padding: "80px 40px 60px",
          borderBottom: "1px solid var(--border-subtle)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background grid */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.03,
            backgroundImage:
              "linear-gradient(var(--border-strong) 1px, transparent 1px), linear-gradient(90deg, var(--border-strong) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
            pointerEvents: "none",
          }}
        />

        <div
          className="animate-fade-up"
          style={{ position: "relative", maxWidth: "600px" }}
        >
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              letterSpacing: "0.14em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              marginBottom: "16px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span className="live-dot" />
            System Active
          </div>

          <h1
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(40px, 6vw, 64px)",
              fontWeight: "400",
              lineHeight: "1.05",
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              marginBottom: "20px",
            }}
          >
            Agentic Quant
            <br />
            <em style={{ fontStyle: "italic", color: "var(--text-secondary)" }}>
              Research Platform
            </em>
          </h1>

          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "15px",
              color: "var(--text-secondary)",
              lineHeight: "1.7",
              maxWidth: "480px",
              marginBottom: "32px",
            }}
          >
            Multi-agent AI pipeline combining quantitative financial algorithms,
            ML models, and LLM reasoning to generate structured investment
            theses.
          </p>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <a href="/dashboard" className="btn btn-primary">
              Open Dashboard →
            </a>
            <a href="/theses" className="btn btn-ghost">
              View Theses
            </a>
          </div>
        </div>
      </div>

      {/* Ticker tape */}
      <div className="ticker-wrap" style={{ padding: "10px 0" }}>
        <div className="ticker-inner">{tickerDisplay}</div>
      </div>

      {/* Stats grid */}
      <div style={{ padding: "32px 40px" }}>
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
          System Status
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: "12px",
            marginBottom: "40px",
          }}
        >
          <StatCard
            label="API Status"
            value={
              status === "online"
                ? "Online"
                : status === "offline"
                  ? "Offline"
                  : "Checking"
            }
            accent={
              status === "online"
                ? "green"
                : status === "offline"
                  ? "red"
                  : "neutral"
            }
            delay={0}
          />
          <StatCard label="Uptime" value={uptime} delay={60} />
          <StatCard label="Algorithms" value="12" sub="Deployed" delay={120} />
          <StatCard
            label="ML Models"
            value="3"
            sub="HMM · XGB · RL"
            delay={180}
          />
          <StatCard label="Agent Nodes" value="4" sub="LangGraph" delay={240} />
        </div>

        {/* Feature grid */}
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
          Capabilities
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
            gap: "12px",
          }}
        >
          {[
            {
              icon: "◈",
              title: "Signal Engine",
              desc: "RSI · MACD · Bollinger · Pairs trading with Kalman filter hedge ratios",
              tag: "Live",
            },
            {
              icon: "◫",
              title: "Pricing & Risk",
              desc: "Black-Scholes · Greeks · VaR · CVaR · Monte Carlo simulation",
              tag: "Live",
            },
            {
              icon: "◧",
              title: "ML Pipeline",
              desc: "HMM regime detection · XGBoost forecaster · SHAP explanations",
              tag: "Live",
            },
            {
              icon: "◬",
              title: "Research Agent",
              desc: "LangGraph pipeline · RAG over filings · Critic revision loop",
              tag: "Live",
            },
          ].map((f, i) => (
            <div
              key={i}
              className="card animate-fade-up"
              style={{
                padding: "20px",
                animationDelay: `${i * 60}ms`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "10px",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "18px",
                    color: "var(--text-tertiary)",
                  }}
                >
                  {f.icon}
                </span>
                <Badge variant="green">{f.tag}</Badge>
              </div>
              <div
                style={{
                  fontFamily: "var(--font-sans)",
                  fontWeight: "500",
                  fontSize: "14px",
                  color: "var(--text-primary)",
                  marginBottom: "6px",
                }}
              >
                {f.title}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--text-tertiary)",
                  lineHeight: "1.6",
                }}
              >
                {f.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
