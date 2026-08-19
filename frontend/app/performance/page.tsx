"use client";

/**
 * AEQUITAS: Benchmarks page
 *
 * Live head-to-head benchmark of the pandas feature-engineering
 * kernels vs their C++20/pybind11 counterparts, run on the API host.
 * Built ahead of a CppCon 2026 talk on this work.
 */

import { Fragment, useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { CardGrid } from "@/components/ui/CardGrid";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { QRFooter } from "@/components/ui/QRFooter";
import { useCountUp } from "@/lib/useCountUp";
import {
  benchmarkApi,
  type BenchmarkResponse,
  type EdgeCaseKernel,
  type EdgeCaseResponse,
  type EdgeCaseScenario,
  type ParallelBenchmarkResponse,
  type PipelineBenchmarkResponse,
  type RealBacktestResponse,
  type ScalingBenchmarkResponse,
} from "@/lib/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";

const BAR_ANIM = { animationDuration: 900, animationEasing: "ease-out" as const };
const IDLE_DEMO_INTERVAL_MS = 30_000;

// Measured on Apple M-series (arm64, 8 cores), Apple clang -O3, 2026-08-15 -
// see backend/cpp/README.md and make_benchmark_chart.py. Shown live as a
// "dev machine (poster)" reference bar so a visitor can see this host vs.
// the printed numbers in one glance instead of needing an explanation.
const POSTER_REFERENCE_SPEEDUP: Record<string, { "10K": number; "100K": number; "1M": number }> = {
  rolling_std_21: { "10K": 4.5, "100K": 3.7, "1M": 4.1 },
  rolling_max_252: { "10K": 1.8, "100K": 1.8, "1M": 1.6 },
  ewm_span_12: { "10K": 1.9, "100K": 1.3, "1M": 1.3 },
  rsi_14: { "10K": 21.8, "100K": 7.1, "1M": 5.9 },
  atr_14: { "10K": 38.7, "100K": 30.4, "1M": 28.9 },
};

function referenceBucket(rows: number): "10K" | "100K" | "1M" {
  if (rows <= 10_000) return "10K";
  if (rows <= 100_000) return "100K";
  return "1M";
}

// The actual code behind each row - click a kernel to see it.
const KERNEL_CODE: Record<string, { pandas: string; cpp: string }> = {
  rolling_std_21: {
    pandas: "s.rolling(21).std()",
    cpp: "ck.rolling_std(x, 21)",
  },
  rolling_max_252: {
    pandas: "s.rolling(252, min_periods=1).max()",
    cpp: "ck.rolling_max(x, 252, 1)",
  },
  ewm_span_12: {
    pandas: "s.ewm(span=12, adjust=False).mean()",
    cpp: "ck.ewm_mean(x, 2/13, 0)",
  },
  rsi_14: {
    pandas: "_rsi(s, 14)  # Wilder smoothing via .ewm(alpha=1/14)",
    cpp: "ck.rsi(x, 14)",
  },
  atr_14: {
    pandas: "_atr(high, low, close, 14)  # true range + .ewm(span=14)",
    cpp: "ck.atr(high, low, close, 14)",
  },
};

const REAL_BACKTEST_TICKERS = ["AAPL", "NVDA", "TSLA"];
const REAL_BACKTEST_YEARS = [1, 5, 10];

const ROW_OPTIONS = [
  { rows: 10_000, label: "10K rows", desc: "~40 years of daily bars" },
  { rows: 100_000, label: "100K rows", desc: "intraday, minutes" },
  { rows: 500_000, label: "500K rows", desc: "multi-symbol scale" },
];

const PIPELINE_ROW_OPTIONS = [
  { rows: 10_000, label: "10K rows" },
  { rows: 50_000, label: "50K rows" },
  { rows: 200_000, label: "200K rows" },
];

const SYMBOL_OPTIONS = [2, 4, 8];

const PARALLEL_ROW_OPTIONS = [
  { rows: 50_000, label: "50K rows" },
  { rows: 200_000, label: "200K rows" },
  { rows: 1_000_000, label: "1M rows" },
];

export default function PerformancePage() {
  const [rows, setRows] = useState(100_000);
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedKernel, setExpandedKernel] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await benchmarkApi.kernels(rows));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Benchmark failed");
    } finally {
      setLoading(false);
    }
    refreshRunCount();
  };

  // -- Live run counter (Redis-backed, "fun fact not audit log") ----
  const [runCount, setRunCount] = useState<number | null>(null);

  const refreshRunCount = () => {
    benchmarkApi
      .runCount()
      .then((r) => setRunCount(r.count))
      .catch(() => {});
  };

  useEffect(() => {
    refreshRunCount();
  }, []);

  const best = data?.results.reduce(
    (a, b) => ((b.speedup ?? 0) > (a?.speedup ?? 0) ? b : a),
    data.results[0],
  );
  const fastest = data?.results.reduce(
    (a, b) => (b.pandas_ms < (a?.pandas_ms ?? Infinity) ? b : a),
    data.results[0],
  );
  const median =
    data && data.cpp_available && data.results.every((r) => r.speedup != null)
      ? [...data.results]
          .map((r) => r.speedup as number)
          .sort((a, b) => a - b)[Math.floor(data.results.length / 2)]
      : null;
  const pandasMedian = data
    ? [...data.results]
        .map((r) => r.pandas_ms)
        .sort((a, b) => a - b)[Math.floor(data.results.length / 2)]
    : null;

  // -- End-to-end pipeline benchmark --------------------------------
  const [pipelineRows, setPipelineRows] = useState(50_000);
  const [pipelineData, setPipelineData] = useState<PipelineBenchmarkResponse | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);

  const runPipeline = async () => {
    setPipelineLoading(true);
    setPipelineError(null);
    try {
      setPipelineData(await benchmarkApi.pipeline(pipelineRows));
    } catch (e) {
      setPipelineError(e instanceof Error ? e.message : "Benchmark failed");
    } finally {
      setPipelineLoading(false);
    }
    refreshRunCount();
  };

  // -- Multi-symbol parallel (GIL release) demo ---------------------
  const [parallelRows, setParallelRows] = useState(200_000);
  const [symbols, setSymbols] = useState(4);
  const [parallelData, setParallelData] = useState<ParallelBenchmarkResponse | null>(null);
  const [parallelLoading, setParallelLoading] = useState(false);
  const [parallelError, setParallelError] = useState<string | null>(null);

  const runParallel = async () => {
    setParallelLoading(true);
    setParallelError(null);
    try {
      setParallelData(await benchmarkApi.parallel(parallelRows, symbols));
    } catch (e) {
      setParallelError(e instanceof Error ? e.message : "Benchmark failed");
    } finally {
      setParallelLoading(false);
    }
    refreshRunCount();
  };

  // -- Thread-count scaling sweep ------------------------------------
  const [scalingData, setScalingData] = useState<ScalingBenchmarkResponse | null>(null);
  const [scalingLoading, setScalingLoading] = useState(false);
  const [scalingError, setScalingError] = useState<string | null>(null);

  const runScaling = async () => {
    setScalingLoading(true);
    setScalingError(null);
    try {
      setScalingData(await benchmarkApi.scaling(parallelRows));
    } catch (e) {
      setScalingError(e instanceof Error ? e.message : "Benchmark failed");
    } finally {
      setScalingLoading(false);
    }
    refreshRunCount();
  };

  // -- Real backtest (real ingested history, not synthetic) -----------
  const [backtestTicker, setBacktestTicker] = useState("AAPL");
  const [backtestYears, setBacktestYears] = useState(5);
  const [backtestData, setBacktestData] = useState<RealBacktestResponse | null>(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  const runBacktest = async () => {
    setBacktestLoading(true);
    setBacktestError(null);
    try {
      setBacktestData(await benchmarkApi.realBacktest(backtestTicker, backtestYears));
    } catch (e) {
      setBacktestError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setBacktestLoading(false);
    }
    refreshRunCount();
  };

  // -- NaN / edge-case explorer ---------------------------------------
  const [edgeKernel, setEdgeKernel] = useState<EdgeCaseKernel>("rolling_std");
  const [edgeScenario, setEdgeScenario] = useState<EdgeCaseScenario>("leading_nan");
  const [edgeData, setEdgeData] = useState<EdgeCaseResponse | null>(null);
  const [edgeLoading, setEdgeLoading] = useState(false);
  const [edgeError, setEdgeError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEdgeLoading(true);
    setEdgeError(null);
    benchmarkApi
      .edgeCase(edgeScenario, edgeKernel)
      .then((r) => {
        if (!cancelled) setEdgeData(r);
      })
      .catch((e) => {
        if (!cancelled) setEdgeError(e instanceof Error ? e.message : "Request failed");
      })
      .finally(() => {
        if (!cancelled) setEdgeLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [edgeKernel, edgeScenario]);

  // -- "Run everything" + kiosk mode ---------------------------------
  const anyLoading = loading || pipelineLoading || parallelLoading;

  const runEverything = async () => {
    await run();
    await runPipeline();
    await runParallel();
  };

  const runEverythingRef = useRef(runEverything);
  runEverythingRef.current = runEverything;

  const [kiosk, setKiosk] = useState(false);

  useEffect(() => {
    if (!kiosk) return;
    const id = setInterval(() => runEverythingRef.current(), IDLE_DEMO_INTERVAL_MS);
    return () => clearInterval(id);
  }, [kiosk]);

  // ?kiosk=1 on the URL turns on kiosk mode and fires the first run
  // immediately - refresh the tab mid-conversation and it demos itself.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("kiosk") === "1") {
      setKiosk(true);
      runEverythingRef.current();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const heroSpeedup = useCountUp(
    parallelData?.cpp_available ? (parallelData.parallel_speedup ?? null) : null,
    900,
  );
  const medianAnimated = useCountUp(data?.cpp_available ? (median ?? null) : null, 700);
  const pipelineSpeedupAnimated = useCountUp(
    pipelineData?.cpp_available ? (pipelineData.speedup ?? null) : null,
    700,
  );

  return (
    <div>
      <PageHeader
        title="Benchmarks"
        subtitle="pandas vs C++20/pybind11 kernels, benchmarked live on the API host"
        serif
      />

      <div style={{ padding: "24px clamp(16px, 5vw, 40px)", display: "grid", gap: 24 }}>
        {/* -- Hero: headline number + run-everything + kiosk mode -- */}
        <div
          className="card animate-fade-up"
          style={{
            padding: "24px clamp(20px, 5vw, 40px)",
            textAlign: "center",
          }}
        >
          {parallelData?.cpp_available && heroSpeedup != null ? (
            <>
              <div className="stat-label">Live right now, on this host</div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontWeight: 500,
                  fontSize: "clamp(28px, 6vw, 40px)",
                  color: "var(--accent-green)",
                  lineHeight: 1.2,
                  margin: "6px 0",
                }}
              >
                {heroSpeedup.toFixed(1)}x faster
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {parallelData.symbols} symbols × {parallelData.rows.toLocaleString()} rows,
                RSI-14 - C++ kernels across {parallelData.cpu_count} threads, GIL released
              </div>
            </>
          ) : (
            <>
              <div
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "clamp(22px, 4vw, 28px)",
                  fontWeight: 400,
                  color: "var(--text-primary)",
                }}
              >
                pandas vs. C++20 - live, on this host
              </div>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 6 }}>
                Hit &ldquo;Run everything&rdquo; to see today&apos;s numbers
              </div>
            </>
          )}

          <div
            style={{
              marginTop: 20,
              display: "flex",
              gap: 12,
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            <button
              onClick={runEverything}
              disabled={anyLoading}
              style={{
                padding: "8px 20px",
                borderRadius: 8,
                border: "none",
                background: "var(--accent-blue)",
                color: "#fff",
                cursor: anyLoading ? "not-allowed" : "pointer",
                opacity: anyLoading ? 0.55 : 1,
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {anyLoading ? "Running..." : "Run everything"}
            </button>
            <button
              onClick={() => setKiosk((k) => !k)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: kiosk
                  ? "1px solid var(--accent-green)"
                  : "1px solid var(--border-subtle)",
                background: kiosk ? "var(--bg-elevated)" : "transparent",
                color: kiosk ? "var(--accent-green)" : "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
              title="Re-runs the full demo automatically every 30s - useful if you're stepping away mid-conversation"
            >
              {kiosk ? "● Kiosk mode: on" : "Kiosk mode: off"}
            </button>
          </div>

          <p
            style={{
              fontSize: 12,
              color: "var(--text-secondary)",
              maxWidth: 640,
              margin: "16px auto 0",
            }}
          >
            Numbers vary by run: parallel speedup is bounded by how many cores this host
            actually has free right now, so a shared cloud instance will show a smaller,
            but equally real, win than an idle 8-core dev machine.
          </p>

          {runCount != null && (
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--text-tertiary)",
                marginTop: 10,
              }}
            >
              {runCount.toLocaleString()} benchmarks run on this host since launch
            </div>
          )}
        </div>

        <SectionHeader
          title="Per-kernel benchmark"
          subtitle="Five rolling-window / exponential-smoothing kernels, isolated"
        />
        {/* Controls */}
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {ROW_OPTIONS.map((o) => (
            <button
              key={o.rows}
              onClick={() => setRows(o.rows)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  rows === o.rows
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: rows === o.rows ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
              title={o.desc}
            >
              {o.label}
            </button>
          ))}
          <button
            onClick={run}
            disabled={loading}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: "var(--accent-blue)",
              color: "#fff",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.55 : 1,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {loading ? "Running..." : "Run benchmark"}
          </button>
          {data && (
            <Badge variant={data.cpp_available ? "green" : "amber"}>
              {data.cpp_available
                ? "C++ extension loaded"
                : "C++ extension not built on this host"}
            </Badge>
          )}
        </div>

        {error && <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{error}</div>}

        {/* Initial run: no prior results to keep on screen, so show a plain spinner. */}
        {loading && !data && (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Spinner size={20} />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "var(--text-tertiary)",
              }}
            >
              Running benchmark...
            </span>
          </div>
        )}

        {/* Re-run: keep the last results visible (dimmed) instead of
            unmounting the whole section and flashing it blank. */}
        {data && (
          <div
            style={{
              display: "grid",
              gap: 24,
              position: "relative",
              opacity: loading ? 0.5 : 1,
              pointerEvents: loading ? "none" : "auto",
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            {loading && (
              <div
                style={{
                  position: "absolute",
                  top: "-28px",
                  right: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <Spinner size={14} />
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    color: "var(--text-tertiary)",
                  }}
                >
                  Re-running...
                </span>
              </div>
            )}

            {!data.cpp_available && (
              <div
                className="card animate-fade-up"
                style={{
                  padding: "14px 18px",
                  background: "var(--bg-elevated)",
                  borderLeft: "3px solid var(--accent-amber)",
                  display: "flex",
                  gap: 10,
                  alignItems: "flex-start",
                  fontSize: 13,
                  color: "var(--text-secondary)",
                }}
              >
                <span
                  aria-hidden="true"
                  style={{ color: "var(--accent-amber)", fontSize: 14, lineHeight: 1.4 }}
                >
                  ●
                </span>
                <span>
                  <strong style={{ color: "var(--text-primary)" }}>
                    C++ extension not built on this host.
                  </strong>{" "}
                  Showing pandas-only timings below. The speedup and numerical-diff
                  columns need the compiled kernel to compare against.
                </span>
              </div>
            )}

            {/* Headline stats */}
            <CardGrid minWidth="180px" gap="16px">
              <StatCard
                label="Dataset"
                value={data.rows.toLocaleString()}
                sub={`rows · median of ${data.reps} runs`}
                delay={0}
              />
              <StatCard
                label={data.cpp_available ? "Median speedup" : "Median pandas time"}
                value={
                  data.cpp_available
                    ? medianAnimated != null
                      ? `${medianAnimated.toFixed(1)}x`
                      : "N/A"
                    : pandasMedian != null
                      ? `${pandasMedian.toFixed(2)}ms`
                      : "N/A"
                }
                sub={data.cpp_available ? "across 5 kernels" : "across 5 kernels, pandas only"}
                accent="blue"
                delay={60}
              />
              <StatCard
                label="Fastest kernel"
                value={
                  data.cpp_available
                    ? best?.speedup != null
                      ? `${best.speedup}x`
                      : "N/A"
                    : fastest
                      ? `${fastest.pandas_ms}ms`
                      : "N/A"
                }
                sub={(data.cpp_available ? best?.kernel : fastest?.kernel) ?? ""}
                accent="green"
                delay={120}
              />
              <StatCard
                label={data.cpp_available ? "Max numerical diff" : "C++ comparison"}
                value={
                  data.cpp_available
                    ? Math.max(...data.results.map((r) => r.max_abs_diff ?? 0)).toExponential(1)
                    : "Not built"
                }
                sub={data.cpp_available ? "pandas vs C++ outputs" : "see kernels README"}
                accent={data.cpp_available ? "neutral" : "amber"}
                delay={180}
              />
              <StatCard
                label="Cold vs warm (pandas)"
                value={`${data.results[0]?.pandas_cold_ms}ms → ${data.results[0]?.pandas_ms}ms`}
                sub="first call vs. median, rolling_std_21"
                accent="neutral"
                delay={220}
              />
              {data.cpp_available && (
                <StatCard
                  label="Cold vs warm (C++)"
                  value={`${data.results[0]?.cpp_cold_ms}ms → ${data.results[0]?.cpp_ms}ms`}
                  sub="first call vs. median, rolling_std_21"
                  accent="neutral"
                  delay={260}
                />
              )}
            </CardGrid>

            {/* Speedup chart: falls back to plain pandas timings when the
                C++ extension isn't built, instead of disappearing entirely.
                When C++ is available, a second "dev machine (poster)" bar
                shows the printed reference number right next to this host's
                live one - no separate explanation needed. */}
            <div className="animate-fade-up" style={{ height: 320, animationDelay: "220ms" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.results.map((r) => ({
                    name: r.kernel,
                    value: data.cpp_available ? r.speedup : r.pandas_ms,
                    reference: POSTER_REFERENCE_SPEEDUP[r.kernel]?.[referenceBucket(rows)],
                  }))}
                  margin={{ top: 24, right: 16, left: 0, bottom: 8 }}
                >
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                    label={{
                      value: data.cpp_available ? "speedup (x)" : "pandas (ms)",
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    formatter={(v: number, name: string) =>
                      data.cpp_available
                        ? [`${v}x`, name === "reference" ? "dev machine (poster)" : "this host"]
                        : [`${v}ms`, "pandas"]
                    }
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "var(--text-primary)",
                    }}
                    itemStyle={{ color: "var(--text-primary)" }}
                    labelStyle={{ color: "var(--text-secondary)" }}
                  />
                  <Bar dataKey="value" name="value" radius={[6, 6, 0, 0]} {...BAR_ANIM}>
                    <LabelList
                      dataKey="value"
                      position="top"
                      formatter={(v: number) => (data.cpp_available ? `${v}x` : `${v}ms`)}
                      style={{ fontSize: 11, fill: "var(--text-secondary)" }}
                    />
                    {data.results.map((r) => (
                      <Cell
                        key={r.kernel}
                        fill={
                          data.cpp_available && (r.speedup ?? 0) >= 10
                            ? "var(--accent-green)"
                            : "var(--accent-blue)"
                        }
                      />
                    ))}
                  </Bar>
                  {data.cpp_available && (
                    <Bar
                      dataKey="reference"
                      name="reference"
                      fill="var(--text-tertiary)"
                      radius={[6, 6, 0, 0]}
                      {...BAR_ANIM}
                    >
                      <LabelList
                        dataKey="reference"
                        position="top"
                        formatter={(v: number) => `${v}x`}
                        style={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                      />
                    </Bar>
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>
            {data.cpp_available && (
              <div style={{ display: "flex", gap: 16, fontSize: 11, color: "var(--text-tertiary)" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 2,
                      background: "var(--accent-blue)",
                      display: "inline-block",
                    }}
                  />
                  this host, live
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: 2,
                      background: "var(--text-tertiary)",
                      display: "inline-block",
                    }}
                  />
                  dev machine, printed on the poster
                </span>
              </div>
            )}

            {/* NumPy middle-ground: does hand-vectorized NumPy get you most
                of the way there, or does pandas' overhead turn out not to
                have been the real bottleneck? Answer varies by kernel -
                sometimes NumPy is even slower than pandas. */}
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                The middle option: hand-vectorized NumPy
              </div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720, marginTop: 4 }}>
                sliding_window_view + scipy.signal.lfilter, no pandas, no C++. Speedup vs.
                pandas - values below 1x mean NumPy was slower.
              </p>
            </div>
            <div className="animate-fade-up" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.results.map((r) => ({
                    name: r.kernel,
                    numpy: r.numpy_speedup ?? 0,
                    cpp: data.cpp_available ? (r.speedup ?? 0) : null,
                  }))}
                  margin={{ top: 24, right: 16, left: 0, bottom: 8 }}
                >
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                    label={{
                      value: "speedup vs pandas (x)",
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    formatter={(v: number, name: string) => [`${v}x`, name]}
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "var(--text-primary)",
                    }}
                    itemStyle={{ color: "var(--text-primary)" }}
                    labelStyle={{ color: "var(--text-secondary)" }}
                  />
                  <Bar dataKey="numpy" name="NumPy" fill="var(--accent-amber)" radius={[6, 6, 0, 0]} {...BAR_ANIM}>
                    <LabelList
                      dataKey="numpy"
                      position="top"
                      formatter={(v: number) => `${v}x`}
                      style={{ fontSize: 10, fill: "var(--text-secondary)" }}
                    />
                  </Bar>
                  {data.cpp_available && (
                    <Bar dataKey="cpp" name="C++" fill="var(--accent-green)" radius={[6, 6, 0, 0]} {...BAR_ANIM}>
                      <LabelList
                        dataKey="cpp"
                        position="top"
                        formatter={(v: number) => `${v}x`}
                        style={{ fontSize: 10, fill: "var(--text-secondary)" }}
                      />
                    </Bar>
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Peak memory: does "zero-copy" actually show up as less
                memory, or does hand-rolled NumPy's windowed view end up
                touching more bytes than pandas along the way? */}
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                Peak memory per call
              </div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720, marginTop: 4 }}>
                tracemalloc peak-traced-memory delta for one isolated call, measured
                separately from the timed runs above so it doesn&apos;t skew them.
              </p>
            </div>
            <div className="animate-fade-up" style={{ height: 280 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.results.map((r) => ({
                    name: r.kernel,
                    pandas: r.pandas_peak_kb,
                    numpy: r.numpy_peak_kb ?? 0,
                    cpp: r.cpp_peak_kb ?? null,
                  }))}
                  margin={{ top: 24, right: 16, left: 0, bottom: 8 }}
                >
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                    label={{
                      value: "peak memory (KB)",
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    formatter={(v: number, name: string) => [`${v.toLocaleString()} KB`, name]}
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "var(--text-primary)",
                    }}
                    itemStyle={{ color: "var(--text-primary)" }}
                    labelStyle={{ color: "var(--text-secondary)" }}
                  />
                  <Bar dataKey="pandas" name="pandas" fill="var(--accent-blue)" radius={[6, 6, 0, 0]} {...BAR_ANIM} />
                  <Bar dataKey="numpy" name="NumPy" fill="var(--accent-amber)" radius={[6, 6, 0, 0]} {...BAR_ANIM} />
                  {data.cpp_available && (
                    <Bar dataKey="cpp" name="C++" fill="var(--accent-green)" radius={[6, 6, 0, 0]} {...BAR_ANIM} />
                  )}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Detail table */}
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    {[
                      "Kernel",
                      "What it computes",
                      "pandas (ms)",
                      "NumPy (ms)",
                      "NumPy speedup",
                      "C++ (ms)",
                      "Speedup",
                      "Max |diff|",
                      "",
                    ].map((h) => (
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
                  {data.results.map((r) => (
                    <Fragment key={r.kernel}>
                      <tr
                        onClick={() =>
                          setExpandedKernel(expandedKernel === r.kernel ? null : r.kernel)
                        }
                        style={{
                          borderBottom:
                            expandedKernel === r.kernel
                              ? "none"
                              : "1px solid var(--border-subtle)",
                          cursor: "pointer",
                        }}
                      >
                        <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                          {r.kernel}
                        </td>
                        <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>
                          {r.description}
                        </td>
                        <td style={{ padding: "8px 12px" }}>{r.pandas_ms}</td>
                        <td style={{ padding: "8px 12px" }}>{r.numpy_ms ?? "N/A"}</td>
                        <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                          {r.numpy_speedup != null ? `${r.numpy_speedup}x` : "N/A"}
                        </td>
                        <td style={{ padding: "8px 12px" }}>{r.cpp_ms ?? "N/A"}</td>
                        <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                          {r.speedup != null ? `${r.speedup}x` : "N/A"}
                        </td>
                        <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                          {r.max_abs_diff != null ? r.max_abs_diff.toExponential(1) : "N/A"}
                        </td>
                        <td
                          style={{
                            padding: "8px 12px",
                            color: "var(--accent-blue)",
                            fontSize: 12,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {expandedKernel === r.kernel ? "▾ hide code" : "▸ view code"}
                        </td>
                      </tr>
                      {expandedKernel === r.kernel && KERNEL_CODE[r.kernel] && (
                        <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                          <td colSpan={9} style={{ padding: "0 12px 12px" }}>
                            <div
                              style={{
                                display: "grid",
                                gap: 8,
                                background: "var(--bg-elevated)",
                                border: "1px solid var(--border-subtle)",
                                borderRadius: 8,
                                padding: 12,
                              }}
                            >
                              <div>
                                <span style={{ fontSize: 11, color: "var(--accent-blue)" }}>
                                  pandas
                                </span>
                                <pre
                                  style={{
                                    margin: "4px 0 0",
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 12,
                                    color: "var(--text-primary)",
                                    whiteSpace: "pre-wrap",
                                  }}
                                >
                                  {KERNEL_CODE[r.kernel].pandas}
                                </pre>
                              </div>
                              <div>
                                <span style={{ fontSize: 11, color: "var(--accent-green)" }}>
                                  C++ (via pybind11)
                                </span>
                                <pre
                                  style={{
                                    margin: "4px 0 0",
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 12,
                                    color: "var(--text-primary)",
                                    whiteSpace: "pre-wrap",
                                  }}
                                >
                                  {KERNEL_CODE[r.kernel].cpp}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {data.note} Speedups vary by host; the spread across kernels is the
              interesting result: largest where the pandas formulation builds intermediate
              DataFrames (ATR), smallest where pandas is already algorithmically efficient
              (rolling max).
            </p>
          </div>
        )}

        {/* -- NaN / edge-case explorer ---------------------------- */}
        <SectionHeader
          title="NaN & edge-case explorer"
          subtitle="Same tiny series, three backends - pick a scenario and watch where they agree, and where they don't"
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {(["rolling_std", "rolling_max"] as EdgeCaseKernel[]).map((k) => (
            <button
              key={k}
              onClick={() => setEdgeKernel(k)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  edgeKernel === k
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: edgeKernel === k ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
                fontFamily: "var(--font-mono)",
              }}
            >
              {k}
            </button>
          ))}
          <span style={{ width: 1, height: 20, background: "var(--border-subtle)" }} />
          {(
            [
              { v: "clean", label: "Clean" },
              { v: "leading_nan", label: "Leading NaN" },
              { v: "interior_nan", label: "Interior NaN" },
              { v: "all_nan", label: "All NaN" },
            ] as { v: EdgeCaseScenario; label: string }[]
          ).map((o) => (
            <button
              key={o.v}
              onClick={() => setEdgeScenario(o.v)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  edgeScenario === o.v
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: edgeScenario === o.v ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {o.label}
            </button>
          ))}
          {edgeLoading && <Spinner size={16} />}
        </div>

        {edgeError && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{edgeError}</div>
        )}

        {edgeData && (
          <div
            style={{
              display: "grid",
              gap: 16,
              opacity: edgeLoading ? 0.5 : 1,
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <Badge variant={edgeData.numpy_matches_pandas ? "green" : "red"}>
                NumPy {edgeData.numpy_matches_pandas ? "matches" : "disagrees"}
              </Badge>
              {edgeData.cpp_available && (
                <Badge variant={edgeData.cpp_matches_pandas ? "green" : "red"}>
                  C++ {edgeData.cpp_matches_pandas ? "matches" : "disagrees"}
                </Badge>
              )}
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", fontSize: 12, fontFamily: "var(--font-mono)" }}>
                <thead>
                  <tr>
                    <th
                      style={{
                        textAlign: "left",
                        padding: "6px 10px",
                        color: "var(--text-secondary)",
                        fontWeight: 500,
                      }}
                    >
                      tick
                    </th>
                    {edgeData.input.map((_, i) => (
                      <th
                        key={i}
                        style={{
                          textAlign: "right",
                          padding: "6px 10px",
                          color: "var(--text-tertiary)",
                          fontWeight: 400,
                        }}
                      >
                        {i}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      { label: "input", values: edgeData.input, mismatch: () => false },
                      { label: "pandas", values: edgeData.pandas, mismatch: () => false },
                      {
                        label: "numpy",
                        values: edgeData.numpy,
                        mismatch: (i: number) => edgeData.numpy[i] !== edgeData.pandas[i],
                      },
                      ...(edgeData.cpp
                        ? [
                            {
                              label: "cpp",
                              values: edgeData.cpp,
                              mismatch: (i: number) =>
                                (edgeData.cpp as (number | null)[])[i] !== edgeData.pandas[i],
                            },
                          ]
                        : []),
                    ] as { label: string; values: (number | null)[]; mismatch: (i: number) => boolean }[]
                  ).map((row) => (
                    <tr key={row.label} style={{ borderTop: "1px solid var(--border-subtle)" }}>
                      <td
                        style={{
                          padding: "6px 10px",
                          color: "var(--text-secondary)",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {row.label}
                      </td>
                      {row.values.map((v, i) => (
                        <td
                          key={i}
                          style={{
                            textAlign: "right",
                            padding: "6px 10px",
                            color: row.mismatch(i) ? "var(--accent-red)" : "var(--text-primary)",
                            background: row.mismatch(i)
                              ? "var(--accent-red-bg)"
                              : "transparent",
                            fontStyle: v == null ? "italic" : "normal",
                          }}
                        >
                          {v == null ? "NaN" : v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {edgeData.note}
            </p>
          </div>
        )}

        {/* -- End-to-end pipeline ------------------------------- */}
        <SectionHeader
          title="End-to-end pipeline"
          subtitle="Full 19-feature compute_features() - pandas vs. the C++-backed drop-in"
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {PIPELINE_ROW_OPTIONS.map((o) => (
            <button
              key={o.rows}
              onClick={() => setPipelineRows(o.rows)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  pipelineRows === o.rows
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: pipelineRows === o.rows ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {o.label}
            </button>
          ))}
          <button
            onClick={runPipeline}
            disabled={pipelineLoading}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: "var(--accent-blue)",
              color: "#fff",
              cursor: pipelineLoading ? "not-allowed" : "pointer",
              opacity: pipelineLoading ? 0.55 : 1,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {pipelineLoading ? "Running..." : "Run pipeline benchmark"}
          </button>
          {pipelineData && (
            <Badge variant={pipelineData.cpp_available ? "green" : "amber"}>
              {pipelineData.cpp_available
                ? "C++ extension loaded"
                : "C++ extension not built on this host"}
            </Badge>
          )}
        </div>

        {pipelineError && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{pipelineError}</div>
        )}

        {pipelineLoading && !pipelineData && (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Spinner size={20} />
            <span
              style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-tertiary)" }}
            >
              Running full pipeline...
            </span>
          </div>
        )}

        {pipelineData && (
          <div
            style={{
              display: "grid",
              gap: 24,
              opacity: pipelineLoading ? 0.5 : 1,
              pointerEvents: pipelineLoading ? "none" : "auto",
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            <CardGrid minWidth="180px" gap="16px">
              <StatCard
                label="Dataset"
                value={pipelineData.rows.toLocaleString()}
                sub={`rows in · ${pipelineData.output_rows.toLocaleString()} out after warm-up`}
              />
              <StatCard
                label="pandas"
                value={`${pipelineData.pandas_ms}ms`}
                sub="full compute_features()"
              />
              <StatCard
                label={pipelineData.cpp_available ? "C++ speedup" : "C++"}
                value={
                  pipelineData.cpp_available
                    ? pipelineSpeedupAnimated != null
                      ? `${pipelineSpeedupAnimated.toFixed(1)}x`
                      : "N/A"
                    : "not built"
                }
                accent={pipelineData.cpp_available ? "green" : "amber"}
              />
              <StatCard
                label="Max numerical diff"
                value={
                  pipelineData.max_abs_diff != null
                    ? pipelineData.max_abs_diff.toExponential(1)
                    : "N/A"
                }
                sub="across all 19 features + target"
                accent="neutral"
              />
            </CardGrid>

            {pipelineData.cpp_available && (
              <div style={{ height: 180 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: "pandas", ms: pipelineData.pandas_ms },
                      { name: "C++", ms: pipelineData.cpp_ms ?? 0 },
                    ]}
                    layout="vertical"
                    margin={{ top: 8, right: 40, left: 16, bottom: 8 }}
                  >
                    <XAxis type="number" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fontSize: 13, fill: "var(--text-secondary)" }}
                      width={60}
                    />
                    <Tooltip
                      formatter={(v: number) => [`${v}ms`, "wall clock"]}
                      contentStyle={{
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 8,
                        fontSize: 12,
                        color: "var(--text-primary)",
                      }}
                      itemStyle={{ color: "var(--text-primary)" }}
                      labelStyle={{ color: "var(--text-secondary)" }}
                    />
                    <Bar dataKey="ms" radius={[0, 6, 6, 0]} {...BAR_ANIM}>
                      <LabelList
                        dataKey="ms"
                        position="right"
                        formatter={(v: number) => `${v}ms`}
                        style={{ fontSize: 11, fill: "var(--text-secondary)" }}
                      />
                      <Cell fill="var(--accent-blue)" />
                      <Cell fill="var(--accent-green)" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {pipelineData.note}
            </p>
          </div>
        )}

        {/* -- Real backtest: the credibility check ---------------- */}
        <SectionHeader
          title="Real backtest, not synthetic"
          subtitle="Same pipeline, but on this platform's own ingested real history for a real ticker"
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {REAL_BACKTEST_TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => setBacktestTicker(t)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  backtestTicker === t
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: backtestTicker === t ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
                fontFamily: "var(--font-mono)",
              }}
            >
              {t}
            </button>
          ))}
          {REAL_BACKTEST_YEARS.map((y) => (
            <button
              key={y}
              onClick={() => setBacktestYears(y)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  backtestYears === y
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: backtestYears === y ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {y}y
            </button>
          ))}
          <button
            onClick={runBacktest}
            disabled={backtestLoading}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: "var(--accent-blue)",
              color: "#fff",
              cursor: backtestLoading ? "not-allowed" : "pointer",
              opacity: backtestLoading ? 0.55 : 1,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {backtestLoading ? "Running..." : "Run real backtest"}
          </button>
        </div>

        {backtestError && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{backtestError}</div>
        )}

        {backtestLoading && !backtestData && (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Spinner size={20} />
            <span
              style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-tertiary)" }}
            >
              Fetching {backtestTicker} history and running MACD backtest...
            </span>
          </div>
        )}

        {backtestData && (
          <div
            style={{
              display: "grid",
              gap: 24,
              opacity: backtestLoading ? 0.5 : 1,
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            <CardGrid minWidth="180px" gap="16px">
              <StatCard
                label="Real history used"
                value={`${backtestData.n_bars.toLocaleString()} bars`}
                sub={`${backtestData.ticker}, ${backtestData.start_date} to ${backtestData.end_date}`}
              />
              <StatCard
                label={backtestData.cpp_available ? "C++ speedup" : "pandas"}
                value={
                  backtestData.cpp_available
                    ? backtestData.speedup != null
                      ? `${backtestData.speedup}x`
                      : "N/A"
                    : `${backtestData.pandas_ms}ms`
                }
                sub="real compute_features(), not synthetic"
                accent={backtestData.cpp_available ? "green" : "amber"}
              />
              <StatCard
                label="Backtest total return"
                value={`${backtestData.total_return_pct}%`}
                sub={`${backtestData.strategy}, ${backtestData.n_trades} trades`}
                accent="blue"
              />
              <StatCard
                label="Results match"
                value={
                  backtestData.backtest_results_match == null
                    ? "N/A"
                    : backtestData.backtest_results_match
                      ? "Yes"
                      : "No"
                }
                sub="pandas-features vs. C++-features backtest outcome"
                accent={
                  backtestData.backtest_results_match === false ? "red" : "neutral"
                }
              />
            </CardGrid>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {backtestData.note} No transaction costs modeled - see
              backend/app/backtesting/engine.py.
            </p>
          </div>
        )}

        {/* -- Multi-symbol parallel (GIL release) ---------------- */}
        <SectionHeader
          title="Multi-symbol parallel (GIL release)"
          subtitle="RSI-14 across N symbols - pandas sequential vs. C++ sequential vs. C++ across a Python ThreadPoolExecutor"
          badge={<Badge variant="green">GIL released during C++ calls</Badge>}
        />
        <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720, marginTop: -8 }}>
          Python&apos;s Global Interpreter Lock normally lets only one thread run Python
          bytecode at a time, so spinning up 8 threads around pandas code doesn&apos;t
          parallelize CPU-bound work at all. Releasing the GIL around the C++ compute
          region (<code style={{ fontFamily: "var(--font-mono)" }}>py::gil_scoped_release</code>)
          is what lets these threads actually run concurrently.
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          {PARALLEL_ROW_OPTIONS.map((o) => (
            <button
              key={o.rows}
              onClick={() => setParallelRows(o.rows)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  parallelRows === o.rows
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: parallelRows === o.rows ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {o.label}
            </button>
          ))}
          {SYMBOL_OPTIONS.map((n) => (
            <button
              key={n}
              onClick={() => setSymbols(n)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border:
                  symbols === n
                    ? "1px solid var(--accent-blue)"
                    : "1px solid var(--border-subtle)",
                background: symbols === n ? "var(--bg-elevated)" : "transparent",
                color: "var(--text-primary)",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {n} symbols
            </button>
          ))}
          <button
            onClick={runParallel}
            disabled={parallelLoading}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: "var(--accent-blue)",
              color: "#fff",
              cursor: parallelLoading ? "not-allowed" : "pointer",
              opacity: parallelLoading ? 0.55 : 1,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {parallelLoading ? "Running..." : "Run parallel demo"}
          </button>
          {parallelData && (
            <Badge variant={parallelData.cpp_available ? "green" : "amber"}>
              {parallelData.cpp_available
                ? `${parallelData.cpu_count}-core host`
                : "C++ extension not built on this host"}
            </Badge>
          )}
        </div>

        {parallelError && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{parallelError}</div>
        )}

        {parallelLoading && !parallelData && (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Spinner size={20} />
            <span
              style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-tertiary)" }}
            >
              Running {symbols}-symbol parallel benchmark...
            </span>
          </div>
        )}

        {parallelData && (
          <div
            style={{
              display: "grid",
              gap: 24,
              opacity: parallelLoading ? 0.5 : 1,
              pointerEvents: parallelLoading ? "none" : "auto",
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            <CardGrid minWidth="180px" gap="16px">
              <StatCard
                label="Workload"
                value={`${parallelData.symbols} × ${parallelData.rows.toLocaleString()}`}
                sub="symbols × rows, RSI-14"
              />
              <StatCard label="pandas sequential" value={`${parallelData.pandas_sequential_ms}ms`} />
              <StatCard
                label={parallelData.cpp_available ? "C++ sequential speedup" : "C++"}
                value={
                  parallelData.cpp_available && parallelData.sequential_speedup != null
                    ? `${parallelData.sequential_speedup}x`
                    : "not built"
                }
                accent="blue"
              />
              <StatCard
                label="C++ parallel speedup"
                value={
                  parallelData.cpp_available && heroSpeedup != null
                    ? `${heroSpeedup.toFixed(1)}x`
                    : "N/A"
                }
                sub={`GIL released, ${parallelData.cpu_count} cores on this host`}
                accent="green"
              />
            </CardGrid>

            {parallelData.cpp_available && (
              <div style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: "pandas (seq)", ms: parallelData.pandas_sequential_ms },
                      { name: "C++ (seq)", ms: parallelData.cpp_sequential_ms ?? 0 },
                      {
                        name: `C++ (${parallelData.symbols}×)`,
                        ms: parallelData.cpp_parallel_ms ?? 0,
                      },
                    ]}
                    margin={{ top: 24, right: 16, left: 0, bottom: 8 }}
                  >
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
                    <YAxis
                      tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                      label={{
                        value: "wall clock (ms)",
                        angle: -90,
                        position: "insideLeft",
                        fontSize: 12,
                      }}
                    />
                    <Tooltip
                      formatter={(v: number) => [`${v}ms`, "wall clock"]}
                      contentStyle={{
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 8,
                        fontSize: 12,
                        color: "var(--text-primary)",
                      }}
                      itemStyle={{ color: "var(--text-primary)" }}
                      labelStyle={{ color: "var(--text-secondary)" }}
                    />
                    <Bar dataKey="ms" radius={[6, 6, 0, 0]} {...BAR_ANIM}>
                      <LabelList
                        dataKey="ms"
                        position="top"
                        formatter={(v: number) => `${v}ms`}
                        style={{ fontSize: 11, fill: "var(--text-secondary)" }}
                      />
                      <Cell fill="var(--text-tertiary)" />
                      <Cell fill="var(--accent-blue)" />
                      <Cell fill="var(--accent-green)" />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {parallelData.note}
            </p>
          </div>
        )}

        {/* -- Thread-count scaling sweep -------------------------- */}
        <SectionHeader
          title="Thread-count scaling"
          subtitle="Fixed workload, varying thread-pool size - where does adding threads stop helping?"
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button
            onClick={runScaling}
            disabled={scalingLoading}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: "var(--accent-blue)",
              color: "#fff",
              cursor: scalingLoading ? "not-allowed" : "pointer",
              opacity: scalingLoading ? 0.55 : 1,
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {scalingLoading ? "Running..." : "Run scaling sweep"}
          </button>
          {scalingData && (
            <Badge variant={scalingData.cpp_available ? "green" : "amber"}>
              {scalingData.cpp_available
                ? `${scalingData.cpu_count}-core host`
                : "C++ extension not built on this host"}
            </Badge>
          )}
        </div>

        {scalingError && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{scalingError}</div>
        )}

        {scalingData && scalingData.points.length > 0 && (
          <div
            style={{
              display: "grid",
              gap: 24,
              opacity: scalingLoading ? 0.5 : 1,
              pointerEvents: scalingLoading ? "none" : "auto",
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          >
            <div style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={scalingData.points.map((p) => ({
                    name: `${p.threads} thread${p.threads > 1 ? "s" : ""}`,
                    ms: p.ms,
                  }))}
                  margin={{ top: 24, right: 16, left: 0, bottom: 8 }}
                >
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                    label={{
                      value: "wall clock (ms)",
                      angle: -90,
                      position: "insideLeft",
                      fontSize: 12,
                    }}
                  />
                  <Tooltip
                    formatter={(v: number) => [`${v}ms`, "wall clock"]}
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "var(--text-primary)",
                    }}
                    itemStyle={{ color: "var(--text-primary)" }}
                    labelStyle={{ color: "var(--text-secondary)" }}
                  />
                  <Bar dataKey="ms" radius={[6, 6, 0, 0]} {...BAR_ANIM}>
                    <LabelList
                      dataKey="ms"
                      position="top"
                      formatter={(v: number) => `${v}ms`}
                      style={{ fontSize: 11, fill: "var(--text-secondary)" }}
                    />
                    {scalingData.points.map((p) => (
                      <Cell
                        key={p.threads}
                        fill={
                          p.threads <= scalingData.cpu_count
                            ? "var(--accent-green)"
                            : "var(--text-tertiary)"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {scalingData.note} Bars beyond this host&apos;s core count are shown in
              gray - more threads than cores rarely helps and can even hurt slightly.
            </p>
          </div>
        )}

        <QRFooter />
      </div>
    </div>
  );
}
