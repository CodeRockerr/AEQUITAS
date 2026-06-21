"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { healthApi } from "@/lib/api";
import { usePriceStream } from "@/hooks/usePriceStream";

const TICKER_LIST = [
  "AAPL",
  "MSFT",
  "SPY",
  "NVDA",
  "TSLA",
  "AMZN",
  "META",
  "GOOGL",
  "BRK-B",
  "JPM",
];

export default function HomePage() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [version, setVersion] = useState("—");
  const { prices, subscribe, unsubscribe, connected } = usePriceStream();

  useEffect(() => {
    healthApi
      .check()
      .then((r) => {
        setStatus("online");
        setVersion(r.version);
      })
      .catch(() => setStatus("offline"));
  }, []);

  // Subscribe to all ticker-tape symbols on mount, unsubscribe on unmount
  useEffect(() => {
    for (const ticker of TICKER_LIST) subscribe(ticker);
    return () => {
      for (const ticker of TICKER_LIST) unsubscribe(ticker);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const tickerItems = [...TICKER_LIST, ...TICKER_LIST].map((ticker, i) => {
    const live = prices[ticker];
    return (
      <span
        key={i}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          padding: "0 24px",
          fontFamily: "var(--font-mono)",
          fontSize: "11px",
          flexShrink: 0,
          opacity: live && !live.isLive ? 0.6 : 1,
        }}
      >
        <span
          style={{ color: "var(--text-secondary)", letterSpacing: "0.06em" }}
        >
          {ticker}
        </span>
        {live ? (
          <>
            <span style={{ color: "var(--text-primary)" }}>
              ${live.price.toFixed(2)}
            </span>
            <span
              style={{
                color:
                  live.changePct >= 0
                    ? "var(--accent-green)"
                    : "var(--accent-red)",
              }}
            >
              {live.changePct >= 0 ? "▲" : "▼"}
              {Math.abs(live.changePct).toFixed(2)}%
            </span>
            {!live.isLive && (
              <span
                style={{
                  color: "var(--text-tertiary)",
                  fontSize: "9px",
                  letterSpacing: "0.04em",
                  textTransform: "uppercase",
                }}
              >
                closed
              </span>
            )}
          </>
        ) : (
          <span style={{ color: "var(--border-strong)" }}>—</span>
        )}
      </span>
    );
  });

  const FEATURES = [
    {
      href: "/dashboard",
      icon: "◈",
      title: "Live Signals",
      desc: "RSI · MACD · Bollinger · Combined momentum score with real-time breakdown",
    },
    {
      href: "/backtests",
      icon: "◫",
      title: "Backtester",
      desc: "RSI · MACD · Bollinger strategies backtested with full tearsheet metrics",
    },
    {
      href: "/theses",
      icon: "◧",
      title: "Agent Theses",
      desc: "4-node LangGraph pipeline generating structured investment theses with citations",
    },
    {
      href: "/risk",
      icon: "◬",
      title: "Risk & Pricing",
      desc: "VaR · CVaR · Monte Carlo · Black-Scholes + Greeks engine",
    },
  ];

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Hero */}
      <div
        style={{
          padding: "72px 40px 64px",
          borderBottom: "1px solid var(--border-subtle)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            backgroundImage:
              "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
            opacity: 0.4,
          }}
        />

        <div style={{ position: "relative", maxWidth: "620px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "4px 12px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "100px",
              marginBottom: "20px",
            }}
          >
            <span
              className="live-dot"
              style={{
                background: connected
                  ? "var(--accent-green)"
                  : "var(--accent-red)",
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                letterSpacing: "0.1em",
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
              }}
            >
              {status === "online"
                ? `API Online · v${version}`
                : status === "offline"
                  ? "API Offline"
                  : "Connecting..."}
              {" · "}
              {connected ? "Live feed connected" : "Reconnecting feed..."}
            </span>
          </div>

          <h1
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(38px, 6vw, 60px)",
              fontWeight: "400",
              lineHeight: "1.05",
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              marginBottom: "18px",
            }}
          >
            Institutional quant
            <br />
            <em style={{ color: "var(--text-secondary)" }}>
              research, automated.
            </em>
          </h1>

          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "15px",
              color: "var(--text-secondary)",
              lineHeight: "1.75",
              maxWidth: "480px",
              marginBottom: "32px",
            }}
          >
            AEQUITAS combines financial algorithms, ML models, and agentic AI to
            generate structured investment theses grounded in real data — in
            seconds.
          </p>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            <Link
              href="/theses"
              className="btn btn-primary"
              style={{ fontSize: "13px", padding: "9px 20px" }}
            >
              Generate a Thesis →
            </Link>
            <Link
              href="/dashboard"
              className="btn btn-ghost"
              style={{ fontSize: "13px", padding: "9px 20px" }}
            >
              View Dashboard
            </Link>
            <Link
              href="/about"
              className="btn btn-ghost"
              style={{ fontSize: "13px", padding: "9px 20px" }}
            >
              About
            </Link>
          </div>
        </div>
      </div>

      {/* Ticker tape — real WebSocket-pushed prices, refreshed every ~12s */}
      <div
        className="ticker-wrap"
        style={{ padding: "8px 0", background: "var(--bg-elevated)" }}
      >
        <div className="ticker-inner">{tickerItems}</div>
      </div>

      {/* Feature cards */}
      <div style={{ padding: "40px 40px 60px" }}>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            letterSpacing: "0.12em",
            color: "var(--text-tertiary)",
            textTransform: "uppercase",
            marginBottom: "14px",
          }}
        >
          Platform
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
            gap: "12px",
          }}
        >
          {FEATURES.map(({ href, icon, title, desc }, i) => (
            <Link key={href} href={href} style={{ textDecoration: "none" }}>
              <div
                className="card"
                style={{
                  padding: "22px",
                  cursor: "pointer",
                  animationDelay: `${i * 60}ms`,
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--border-strong)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "";
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "12px",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "20px",
                      color: "var(--text-tertiary)",
                    }}
                  >
                    {icon}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      color: "var(--accent-green)",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Live →
                  </span>
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
                  {title}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-tertiary)",
                    lineHeight: "1.6",
                  }}
                >
                  {desc}
                </div>
              </div>
            </Link>
          ))}
        </div>

        {/* Quick stats */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
            gap: "1px",
            background: "var(--border-subtle)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            overflow: "hidden",
            marginTop: "24px",
          }}
        >
          {[
            { v: "121", l: "Unit Tests" },
            { v: "13", l: "Algorithms" },
            { v: "4", l: "Agent Nodes" },
            { v: "3", l: "ML Models" },
            { v: "7", l: "API Routers" },
            { v: "v0.9", l: "Version" },
          ].map(({ v, l }) => (
            <div
              key={l}
              style={{
                background: "var(--bg-surface)",
                padding: "16px 20px",
              }}
            >
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "20px",
                  fontWeight: "500",
                  color: "var(--text-primary)",
                  letterSpacing: "-0.01em",
                  lineHeight: 1,
                  marginBottom: "4px",
                }}
              >
                {v}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  letterSpacing: "0.08em",
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                }}
              >
                {l}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
