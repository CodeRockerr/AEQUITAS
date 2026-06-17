"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { healthApi } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

interface TickerPrice {
  ticker: string;
  price: number | null;
  change: number | null;
}

export default function HomePage() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [version, setVersion] = useState("—");
  const [prices, setPrices] = useState<TickerPrice[]>(
    TICKER_LIST.map((t) => ({ ticker: t, price: null, change: null })),
  );

  useEffect(() => {
    healthApi
      .check()
      .then((r) => {
        setStatus("online");
        setVersion(r.version);
      })
      .catch(() => setStatus("offline"));
  }, []);

  // Fetch real prices from our market data endpoint
  useEffect(() => {
    async function fetchPrices() {
      const results = await Promise.allSettled(
        TICKER_LIST.map(async (ticker) => {
          const res = await fetch(
            `${API_BASE}/api/v1/market-data/${ticker}/bars?limit=2&interval=1d`,
            { cache: "no-store" },
          );
          if (!res.ok) return { ticker, price: null, change: null };
          const bars = (await res.json()) as Array<{ close: string }>;
          if (bars.length < 2)
            return {
              ticker,
              price: parseFloat(bars[0]?.close ?? "0"),
              change: null,
            };
          const price = parseFloat(bars[bars.length - 1].close);
          const prev = parseFloat(bars[bars.length - 2].close);
          const change = ((price - prev) / prev) * 100;
          return { ticker, price, change };
        }),
      );
      setPrices(
        results.map((r, i) =>
          r.status === "fulfilled"
            ? r.value
            : { ticker: TICKER_LIST[i], price: null, change: null },
        ),
      );
    }
    void fetchPrices();
    const id = setInterval(() => void fetchPrices(), 60_000);
    return () => clearInterval(id);
  }, []);

  const tickerItems = [...prices, ...prices].map((p, i) => (
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
      }}
    >
      <span style={{ color: "var(--text-secondary)", letterSpacing: "0.06em" }}>
        {p.ticker}
      </span>
      {p.price !== null ? (
        <>
          <span style={{ color: "var(--text-primary)" }}>
            ${p.price.toFixed(2)}
          </span>
          {p.change !== null && (
            <span
              style={{
                color:
                  p.change >= 0 ? "var(--accent-green)" : "var(--accent-red)",
              }}
            >
              {p.change >= 0 ? "▲" : "▼"}
              {Math.abs(p.change).toFixed(2)}%
            </span>
          )}
        </>
      ) : (
        <span style={{ color: "var(--border-strong)" }}>—</span>
      )}
    </span>
  ));

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
            <span className="live-dot" />
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

      {/* Ticker tape — real prices */}
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
            { v: "87", l: "Unit Tests" },
            { v: "12", l: "Algorithms" },
            { v: "4", l: "Agent Nodes" },
            { v: "3", l: "ML Models" },
            { v: "6", l: "API Routers" },
            { v: "v0.7", l: "Version" },
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
