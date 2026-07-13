"""
Generate the benchmark figure.

Data: measured on Apple M-series (arm64, 8 cores), Apple clang -O3,
Python 3.13, median of 7 runs (5 for multi-symbol). Source: benchmark.py
run on 2026-07-13 by Adit Shah.

Usage: python3 make_benchmark_chart.py
Outputs: benchmark_chart.png (300 dpi, for the PDF) and .svg (for the poster)
"""

import matplotlib.pyplot as plt
import numpy as np

# ── Measured data (Mac, arm64) ────────────────────────────────
KERNELS = ["rolling_std(21)", "rolling_max(252)", "ewm(span=12)", "rsi(14)", "atr(14)"]
SIZES = ["10K", "100K", "1M"]
SPEEDUP = {  # kernel -> [10K, 100K, 1M]
    "rolling_std(21)": [6.8, 5.8, 5.7],
    "rolling_max(252)": [2.0, 1.8, 1.7],
    "ewm(span=12)": [2.0, 1.3, 1.3],
    "rsi(14)": [24.7, 7.4, 5.8],
    "atr(14)": [40.0, 28.1, 26.8],
}
# multi-symbol RSI, 8 x 1M rows, ms
PARALLEL = [
    ("pandas\nsequential", 194.3),
    ("C++\nsequential", 33.5),
    ("C++\n8 threads", 4.9),
]

INK = "#1a1a2e"
BLUES = ["#a8c5e8", "#5b8bc9", "#1f4e8c"]
GREEN = "#2e7d52"

fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.7, 1]}
)
fig.patch.set_facecolor("white")

# ── Panel 1: per-kernel speedup by dataset size ───────────────
x = np.arange(len(KERNELS))
w = 0.26
for i, size in enumerate(SIZES):
    vals = [SPEEDUP[k][i] for k in KERNELS]
    bars = ax1.bar(x + (i - 1) * w, vals, w, label=f"{size} rows", color=BLUES[i])
    for b, v in zip(bars, vals, strict=False):
        yoff = (
            1.06 if i != 1 else 1.22
        )  # stagger middle series to avoid label collisions
        ax1.text(
            b.get_x() + b.get_width() / 2,
            v * yoff,
            f"{v:g}x",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=INK,
        )

ax1.axhline(1, color="#999", lw=0.8, ls="--")
ax1.text(len(KERNELS) - 0.45, 1.08, "parity", fontsize=7.5, color="#777")
ax1.set_yscale("log")
ax1.set_ylim(0.8, 90)
ax1.set_yticks([1, 2, 5, 10, 20, 40, 80])
ax1.set_yticklabels(["1x", "2x", "5x", "10x", "20x", "40x", "80x"])
ax1.set_xticks(x)
ax1.set_xticklabels(KERNELS, fontsize=8.5)
ax1.set_ylabel("speedup vs pandas (log scale)", fontsize=9)
ax1.set_title("C++20 kernel speedup vs pandas, by dataset size", fontsize=10, color=INK)
ax1.legend(fontsize=8, frameon=False)
ax1.spines[["top", "right"]].set_visible(False)

# ── Panel 2: multi-symbol parallel (the GIL-release payoff) ───
labels = [p[0] for p in PARALLEL]
times = [p[1] for p in PARALLEL]
colors = ["#b0b0b0", BLUES[2], GREEN]
bars = ax2.bar(labels, times, 0.6, color=colors)
for b, t in zip(bars, times, strict=False):
    ax2.text(
        b.get_x() + b.get_width() / 2,
        t * 1.1,
        f"{t:g} ms",
        ha="center",
        va="bottom",
        fontsize=9,
        color=INK,
        fontweight="bold",
    )
ax2.text(
    2,
    times[0] * 0.55,
    "39.8x\nend-to-end",
    ha="center",
    fontsize=9,
    color=GREEN,
    fontweight="bold",
)
ax2.set_yscale("log")
ax2.set_ylim(3, 500)
ax2.set_ylabel("wall clock, ms (log scale)", fontsize=9)
ax2.set_title(
    "RSI-14, 8 symbols × 1M rows\n(ThreadPoolExecutor + GIL release)",
    fontsize=10,
    color=INK,
)
ax2.spines[["top", "right"]].set_visible(False)

fig.text(
    0.5,
    -0.04,
    "Apple M-series (arm64, 8 cores), Apple clang -O3, Python 3.13 — median of repeated runs; "
    "identical synthetic OHLCV inputs; outputs verified equal to pandas to ≤4e-9",
    ha="center",
    fontsize=7.5,
    color="#666",
)

plt.tight_layout()
for ext in ("png", "svg"):
    fig.savefig(
        f"benchmark_chart.{ext}", dpi=300, bbox_inches="tight", facecolor="white"
    )
print("wrote benchmark_chart.png and benchmark_chart.svg")
