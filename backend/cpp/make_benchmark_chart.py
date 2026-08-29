"""
Generate the benchmark figure from hardcoded, hand-measured numbers.

Data: measured on Apple M2 (arm64, 8 cores), Apple clang -O3,
Python 3.13.5, median of 7 runs (3 for multi-symbol). Source: benchmark.py
run on 2026-08-29 by Adit Shah. Per-kernel 1M-row range is 1.3x-27.4x;
the 10K ATR 39.5x is pandas call overhead at small n, shown on the chart
but not used as the headline. Multi-symbol RSI is 37.7x (197.5 -> 5.2 ms).

For a chart built from a live, running API host instead of numbers
pasted in by hand, see make_live_benchmark_chart.py.

Usage: python3 make_benchmark_chart.py
Outputs: benchmark_chart.png (300 dpi, for the PDF) and .svg (for the poster)
"""

from _chart import draw_benchmark_figure

# -- Measured data (Apple M2, arm64, 2026-08-29) ---------------
SIZE_LABELS = ["10K", "100K", "1M"]
SPEEDUP = {  # kernel -> [10K, 100K, 1M]
    "rolling_std(21)": [4.4, 3.6, 3.6],
    "rolling_max(252)": [2.0, 1.8, 1.7],
    "ewm(span=12)": [1.9, 1.3, 1.3],
    "rsi(14)": [20.8, 7.1, 5.9],
    "atr(14)": [39.5, 28.2, 27.4],
}
# multi-symbol RSI, 8 x 1M rows, ms
PARALLEL = [
    ("pandas\nsequential", 197.5),
    ("C++\nsequential", 33.9),
    ("C++\n8 threads", 5.2),
]

CAPTION = (
    "Apple M2 (arm64, 8 cores), Apple clang -O3, Python 3.13.5 - median of "
    "7 runs (3 for multi-symbol); identical synthetic OHLCV; outputs agree "
    "with pandas to ≤1.1e-8 (most kernels ≤1e-12 or exact)"
)

if __name__ == "__main__":
    draw_benchmark_figure(
        SPEEDUP,
        SIZE_LABELS,
        PARALLEL,
        CAPTION,
        "benchmark_chart",
        parallel_subtitle="8 symbols × 1M rows",
    )
