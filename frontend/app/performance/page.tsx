"use client";

/**
 * AEQUITAS — Performance page
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
import { benchmarkApi, type BenchmarkResponse } from "@/lib/api";
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
  const median =
    data && data.results.every((r) => r.speedup != null)
      ? [...data.results]
          .map((r) => r.speedup as number)
          .sort((a, b) => a - b)[Math.floor(data.results.length / 2)]
      : null;

  return (
    <div>
      <PageHeader
        title="Python vs C++"
        subtitle="Feature kernels benchmarked live on the API host — pandas vs C++20/pybind11"
        serif
      />

      <div style={{ padding: "24px 40px", display: "grid", gap: 24 }}>
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
              cursor: loading ? "wait" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {loading ? "Running…" : "Run benchmark"}
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
        {loading && <Spinner />}

        {data && !loading && (
          <>
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
              />
              <StatCard
                label="Median speedup"
                value={median != null ? `${median}x` : "—"}
                sub="across 5 kernels"
                accent="blue"
              />
              <StatCard
                label="Best kernel"
                value={best?.speedup != null ? `${best.speedup}x` : "—"}
                sub={best?.kernel ?? ""}
                accent="green"
              />
              <StatCard
                label="Max numerical diff"
                value={
                  data.cpp_available
                    ? Math.max(
                        ...data.results.map((r) => r.max_abs_diff ?? 0),
                      ).toExponential(1)
                    : "—"
                }
                sub="pandas vs C++ outputs"
              />
            </div>

            {/* Speedup chart */}
            {data.cpp_available && (
              <div style={{ height: 320 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={data.results.map((r) => ({
                      name: r.kernel,
                      speedup: r.speedup,
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
                        value: "speedup (x)",
                        angle: -90,
                        position: "insideLeft",
                        fontSize: 12,
                      }}
                    />
                    <Tooltip
                      formatter={(v: number) => [`${v}x`, "speedup"]}
                      contentStyle={{
                        background: "var(--bg-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="speedup" radius={[6, 6, 0, 0]}>
                      <LabelList
                        dataKey="speedup"
                        position="top"
                        formatter={(v: number) => `${v}x`}
                        style={{ fontSize: 11, fill: "var(--text-secondary)" }}
                      />
                      {data.results.map((r) => (
                        <Cell
                          key={r.kernel}
                          fill={
                            (r.speedup ?? 0) >= 10
                              ? "var(--accent-green)"
                              : "var(--accent-blue)"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

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
                    <td style={{ padding: "8px 12px" }}>{r.cpp_ms ?? "—"}</td>
                    <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                      {r.speedup != null ? `${r.speedup}x` : "—"}
                    </td>
                    <td style={{ padding: "8px 12px", fontFamily: "var(--font-mono)" }}>
                      {r.max_abs_diff != null ? r.max_abs_diff.toExponential(1) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p style={{ fontSize: 12, color: "var(--text-secondary)", maxWidth: 720 }}>
              {data.note} Speedups vary by host; the spread across kernels is
              the interesting result — largest where the pandas formulation
              builds intermediate DataFrames (ATR), smallest where pandas is
              already algorithmically efficient (rolling max).
            </p>
          </>
        )}
      </div>
    </div>
  );
}
