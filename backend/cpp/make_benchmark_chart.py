"""
Generate the benchmark figure from hardcoded, hand-measured numbers.

Data: measured on Apple M-series (arm64, 8 cores), Apple clang -O3,
Python 3.13, median of 7 runs (5 for multi-symbol). Source: benchmark.py
run on 2026-08-15 by Adit Shah, after fixing a NaN self-recovery bug in
rolling_mean/rolling_std (see kernels.cpp and the README's "Lessons
learned" section) - the fix only changes correctness on NaN-containing
input, not these clean-input numbers, which are consistent run-to-run
with the original submission.

For a chart built from a live, running API host instead of numbers
pasted in by hand, see make_live_benchmark_chart.py.

Usage: python3 make_benchmark_chart.py
Outputs: benchmark_chart.png (300 dpi, for the PDF) and .svg (for the poster)
"""

from _chart import draw_benchmark_figure

# -- Measured data (Mac, arm64) --------------------------------
SIZE_LABELS = ["10K", "100K", "1M"]
SPEEDUP = {  # kernel -> [10K, 100K, 1M]
    "rolling_std(21)": [4.5, 3.7, 4.1],
    "rolling_max(252)": [1.8, 1.8, 1.6],
    "ewm(span=12)": [1.9, 1.3, 1.3],
    "rsi(14)": [21.8, 7.1, 5.9],
    "atr(14)": [38.7, 30.4, 28.9],
}
# multi-symbol RSI, 8 x 1M rows, ms
PARALLEL = [
    ("pandas\nsequential", 202.0),
    ("C++\nsequential", 33.9),
    ("C++\n8 threads", 8.9),
]

CAPTION = (
    "Apple M-series (arm64, 8 cores), Apple clang -O3, Python 3.13 - median of "
    "repeated runs; identical synthetic OHLCV inputs; outputs verified equal to "
    "pandas to ≤4e-9"
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
