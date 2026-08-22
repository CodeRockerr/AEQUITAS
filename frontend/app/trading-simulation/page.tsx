"use client";

/**
 * AEQUITAS: Trading Simulation page
 *
 * Synthetic tick-by-tick price feed. Every new bar recomputes a
 * buy/sell/hold RSI signal two ways - pandas (the platform's real
 * signal-generation code) and the C++20 kernel - and times each one.
 * No real broker, no real orders, no real money.
 */

import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { CardGrid } from "@/components/ui/CardGrid";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { QRFooter } from "@/components/ui/QRFooter";
import { SimulationDiagram } from "@/components/ui/SimulationDiagram";

const LIVE_DECISION_WS_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^http/, "ws") +
  "/ws/live-decision";
const MAX_LIVE_TICKS_SHOWN = 10;
const REAL_TICKERS = ["AAPL", "NVDA", "TSLA"];

interface LiveTick {
  seq: number;
  ticker: string | null;
  price: number;
  decision: "BUY" | "SELL" | "HOLD" | "WARMING_UP";
  signal: number;
  pandas_us: number | null;
  cpp_us: number | null;
  speedup: number | null;
  cpp_available: boolean;
}

function decisionBadgeVariant(d: LiveTick["decision"]): "green" | "red" | "neutral" | "amber" {
  if (d === "BUY") return "green";
  if (d === "SELL") return "red";
  if (d === "WARMING_UP") return "amber";
  return "neutral";
}

function formatUs(us: number | null): string {
  if (us == null) return "N/A";
  return us < 1000 ? `${us.toFixed(0)}µs` : `${(us / 1000).toFixed(2)}ms`;
}

export default function TradingSimulationPage() {
  const [liveConnected, setLiveConnected] = useState(false);
  const [liveTicks, setLiveTicks] = useState<LiveTick[]>([]);
  const [liveTotals, setLiveTotals] = useState({ count: 0, pandasUs: 0, cppUs: 0 });
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const liveWsRef = useRef<WebSocket | null>(null);

  const stopLiveDemo = () => {
    liveWsRef.current?.close();
    liveWsRef.current = null;
    setLiveConnected(false);
  };

  const startLiveDemo = () => {
    if (liveWsRef.current) return;
    setLiveError(null);
    setLiveTicks([]);
    setLiveTotals({ count: 0, pandasUs: 0, cppUs: 0 });
    const url = selectedTicker
      ? `${LIVE_DECISION_WS_BASE}?ticker=${selectedTicker}`
      : LIVE_DECISION_WS_BASE;
    const ws = new WebSocket(url);
    liveWsRef.current = ws;

    ws.onopen = () => setLiveConnected(true);
    ws.onclose = () => {
      liveWsRef.current = null;
      setLiveConnected(false);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.type === "error") {
          setLiveError(parsed.detail ?? "Live feed error");
          ws.close();
          return;
        }
        const tick: LiveTick = parsed;
        setLiveTicks((prev) => [tick, ...prev].slice(0, MAX_LIVE_TICKS_SHOWN));
        if (tick.pandas_us != null && tick.cpp_us != null) {
          setLiveTotals((prev) => ({
            count: prev.count + 1,
            pandasUs: prev.pandasUs + (tick.pandas_us as number),
            cppUs: prev.cppUs + (tick.cpp_us as number),
          }));
        }
      } catch {
        // ignore malformed messages
      }
    };
  };

  useEffect(() => {
    return () => {
      liveWsRef.current?.close();
    };
  }, []);

  const liveAvgPandasUs = liveTotals.count > 0 ? liveTotals.pandasUs / liveTotals.count : null;
  const liveAvgCppUs = liveTotals.count > 0 ? liveTotals.cppUs / liveTotals.count : null;
  const liveAvgSpeedup =
    liveAvgPandasUs != null && liveAvgCppUs != null && liveAvgCppUs > 0
      ? liveAvgPandasUs / liveAvgCppUs
      : null;

  return (
    <div>
      <PageHeader
        title="Trading Simulation"
        subtitle="Synthetic tick feed - RSI buy/sell/hold decisions, pandas vs. C++, timed live"
        serif
      />

      <div style={{ padding: "24px clamp(16px, 5vw, 40px)", display: "grid", gap: 24 }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 720, margin: "0 auto" }}>
          This streams a price feed - synthetic random-walk by default, or this
          platform&apos;s own ingested real daily history for a ticker, replayed
          tick-by-tick - no real broker, no real orders, no real money either way.
          Every new bar re-runs the platform&apos;s actual RSI signal logic (
          <code style={{ fontFamily: "var(--font-mono)" }}>
            app/algorithms/signals/momentum.py
          </code>
          ) once in pandas and once through the same C++20 kernel from the{" "}
          <code style={{ fontFamily: "var(--font-mono)" }}>Benchmarks</code> page, and
          times both. The point isn&apos;t the trading strategy - it&apos;s what faster
          kernels buy you in a system that has to decide on every tick.
        </p>

        <SimulationDiagram
          pandasLabel={liveAvgPandasUs != null ? formatUs(liveAvgPandasUs) : "~2-8ms typical"}
          cppLabel={liveAvgCppUs != null ? formatUs(liveAvgCppUs) : "~10-500µs typical"}
        />

        <SectionHeader
          centered
          title="Live trading decision latency"
          subtitle="Start the feed and watch each tick's decision, and its latency, land in real time"
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div
            style={{
              display: "flex",
              gap: 12,
              opacity: liveConnected ? 0.4 : 1,
              pointerEvents: liveConnected ? "none" : "auto",
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            <button
              onClick={() => setSelectedTicker(null)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  selectedTicker == null
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: selectedTicker == null ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              Synthetic
            </button>
            {REAL_TICKERS.map((t) => (
              <button
                key={t}
                onClick={() => setSelectedTicker(t)}
                style={{
                  padding: "8px 16px",
                  borderRadius: 8,
                  border:
                    selectedTicker === t
                      ? "1px solid var(--accent-blue)"
                      : "1px solid var(--border-subtle)",
                  background: selectedTicker === t ? "var(--bg-elevated)" : "transparent",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                {t}
              </button>
            ))}
          </div>
          <button
            onClick={liveConnected ? stopLiveDemo : startLiveDemo}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: liveConnected ? "var(--accent-red)" : "var(--accent-blue)",
              color: "#fff",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {liveConnected ? "Stop feed" : "Start live feed"}
          </button>
          {liveConnected && (
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="live-dot" />
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--accent-green)",
                }}
              >
                streaming
              </span>
            </span>
          )}
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            {selectedTicker
              ? `Real ${selectedTicker} history, replayed - no real broker, no real orders`
              : "Synthetic price feed - no real broker, no real orders"}
          </span>
        </div>

        {liveError && (
          <div style={{ color: "var(--accent-red)", fontSize: 13, textAlign: "center" }}>
            {liveError}
          </div>
        )}

        {liveTicks.length > 0 && (
          <div style={{ display: "grid", gap: 24 }}>
            <CardGrid minWidth="180px" gap="16px">
              <StatCard
                label="Decisions made"
                value={liveTotals.count.toLocaleString()}
                sub="ticks past warm-up"
              />
              <StatCard
                label="Avg pandas latency"
                value={formatUs(liveAvgPandasUs)}
                sub="per-tick decision"
              />
              <StatCard
                label="Avg C++ latency"
                value={formatUs(liveAvgCppUs)}
                sub="per-tick decision"
                accent="blue"
              />
              <StatCard
                label="Avg speedup"
                value={liveAvgSpeedup != null ? `${liveAvgSpeedup.toFixed(1)}x` : "N/A"}
                sub="faster time-to-decision"
                accent="green"
              />
            </CardGrid>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    {["Tick", "Price", "Decision", "pandas", "C++", "Speedup"].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "8px 12px",
                          color: "var(--text-secondary)",
                          fontWeight: 500,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {liveTicks.map((t) => (
                    <tr key={t.seq} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                        #{t.seq}
                      </td>
                      <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                        ${t.price.toFixed(2)}
                      </td>
                      <td style={{ padding: "8px 12px" }}>
                        <Badge variant={decisionBadgeVariant(t.decision)}>{t.decision}</Badge>
                      </td>
                      <td style={{ padding: "8px 12px" }}>{formatUs(t.pandas_us)}</td>
                      <td style={{ padding: "8px 12px" }}>{formatUs(t.cpp_us)}</td>
                      <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                        {t.speedup != null ? `${t.speedup}x` : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720, margin: "0 auto" }}>
              Same RSI-14 kernel as the per-kernel benchmark, run once per incoming tick
              on a 250-bar rolling window and timed both ways - the concrete version of
              &ldquo;faster kernels&rdquo;: faster time-to-decision on every new bar, not
              just a synthetic benchmark number.
            </p>
          </div>
        )}

        <QRFooter />
      </div>
    </div>
  );
}
