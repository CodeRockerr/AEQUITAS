"use client";

/**
 * AEQUITAS: Performance page
 *
 * Live head-to-head benchmark of the pandas feature-engineering
 * kernels vs their C++20/pybind11 counterparts, run on the API host.
 * Companion demo for the CppCon 2026 poster.
 */

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import {
  benchmarkApi,
  type BenchmarkResponse,
  type ParallelBenchmarkResponse,
  type PipelineBenchmarkResponse,
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

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div style={{ marginTop: 8 }}>
      <h2
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: "var(--text-primary)",
          margin: 0,
        }}
      >
        {title}
      </h2>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
        {subtitle}
      </p>
    </div>
  );
}

export default function PerformancePage() {
  const [rows, setRows] = useState(100_000);
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
  };

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

  // ── End-to-end pipeline benchmark ──────────────────────────────
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
  };

  // ── Multi-symbol parallel (GIL release) demo ───────────────────
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
  };

  return (
    <div>
      <PageHeader
        title="Python vs C++"
        subtitle="CppCon 2026 poster companion — pandas vs C++20/pybind11 kernels, benchmarked live on the API host"
        serif
      />

      <div style={{ padding: "24px 40px", display: "grid", gap: 24 }}>
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

        {error && (
          <div style={{ color: "var(--accent-red)", fontSize: 13 }}>{error}</div>
        )}

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
                  Showing pandas-only timings below. The speedup and
                  numerical-diff columns need the compiled kernel to compare
                  against.
                </span>
              </div>
            )}

            {/* Headline stats */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 16,
              }}
            >
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
                    ? median != null
                      ? `${median}x`
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
                    ? Math.max(
                        ...data.results.map((r) => r.max_abs_diff ?? 0),
                      ).toExponential(1)
                    : "Not built"
                }
                sub={data.cpp_available ? "pandas vs C++ outputs" : "see kernels README"}
                accent={data.cpp_available ? "neutral" : "amber"}
                delay={180}
              />
            </div>

            {/* Speedup chart: falls back to plain pandas timings when the
                C++ extension isn't built, instead of disappearing entirely */}
            <div className="animate-fade-up" style={{ height: 320, animationDelay: "220ms" }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.results.map((r) => ({
                    name: r.kernel,
                    value: data.cpp_available ? r.speedup : r.pandas_ms,
                  }))}
                  margin={{ top: 24, right: 16, left: 0, bottom: 8 }}
                >
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
                  />
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
                    formatter={(v: number) =>
                      data.cpp_available ? [`${v}x`, "speedup"] : [`${v}ms`, "pandas"]
                    }
                    contentStyle={{
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
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
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Detail table */}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  {["Kernel", "What it computes", "pandas (ms)", "C++ (ms)", "Speedup", "Max |diff|"].map(
                    (h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "8px 12px",
                          color: "var(--text-secondary)",
                          fontWeight: 500,
                        }}
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr
                    key={r.kernel}
                    style={{ borderBottom: "1px solid var(--border-subtle)" }}
                  >
                    <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                      {r.kernel}
                    </td>
                    <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>
                      {r.description}
                    </td>
                    <td style={{ padding: "8px 12px" }}>{r.pandas_ms}</td>
                    <td style={{ padding: "8px 12px" }}>{r.cpp_ms ?? "N/A"}</td>
                    <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                      {r.speedup != null ? `${r.speedup}x` : "N/A"}
                    </td>
                    <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                      {r.max_abs_diff != null ? r.max_abs_diff.toExponential(1) : "N/A"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {data.note} Speedups vary by host; the spread across kernels is
              the interesting result: largest where the pandas formulation
              builds intermediate DataFrames (ATR), smallest where pandas is
              already algorithmically efficient (rolling max).
            </p>
          </div>
        )}

        {/* ── End-to-end pipeline ─────────────────────────────── */}
        <SectionHeader
          title="End-to-end pipeline"
          subtitle="Full 19-feature compute_features() — pandas vs. the C++-backed drop-in"
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
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 16,
              }}
            >
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
                    ? pipelineData.speedup != null
                      ? `${pipelineData.speedup}x`
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
            </div>

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
                      }}
                    />
                    <Bar dataKey="ms" radius={[0, 6, 6, 0]}>
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

        {/* ── Multi-symbol parallel (GIL release) ────────────────── */}
        <SectionHeader
          title="Multi-symbol parallel (GIL release)"
          subtitle="RSI-14 across N symbols — the poster's headline result: pandas sequential vs. C++ sequential vs. C++ across a Python ThreadPoolExecutor"
        />
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
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 16,
              }}
            >
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
                  parallelData.cpp_available && parallelData.parallel_speedup != null
                    ? `${parallelData.parallel_speedup}x`
                    : "N/A"
                }
                sub={`GIL released, ${parallelData.cpu_count} cores on this host`}
                accent="green"
              />
            </div>

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
                      }}
                    />
                    <Bar dataKey="ms" radius={[6, 6, 0, 0]}>
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
      </div>
    </div>
  );
}
