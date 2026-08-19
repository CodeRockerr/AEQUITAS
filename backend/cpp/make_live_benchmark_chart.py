"""
Generate the benchmark figure from a LIVE, running API host - not numbers
pasted in by hand.

make_benchmark_chart.py uses constants you update manually after running
benchmark.py locally. This script instead calls /api/v1/benchmark/kernels
and /api/v1/benchmark/parallel on a real host (default: localhost, or pass
--host to point at the deployed production API) and draws the same figure
from whatever that host measures right now - so the printed poster can
reflect reality right up to the print deadline, not a snapshot from
whenever someone last ran the numbers by hand.

Usage:
    python3 make_live_benchmark_chart.py
    python3 make_live_benchmark_chart.py --host https://aequitas-api.onrender.com
    python3 make_live_benchmark_chart.py --host https://aequitas-api.onrender.com \
        --parallel-rows 500000 --parallel-symbols 4
"""

import argparse
import json
import sys
import urllib.request
from datetime import UTC, datetime

from _chart import draw_benchmark_figure

KERNEL_ORDER = ["rolling_std_21", "rolling_max_252", "ewm_span_12", "rsi_14", "atr_14"]
KERNEL_LABELS = {
    "rolling_std_21": "rolling_std(21)",
    "rolling_max_252": "rolling_max(252)",
    "ewm_span_12": "ewm(span=12)",
    "rsi_14": "rsi(14)",
    "atr_14": "atr(14)",
}
# /benchmark/kernels caps at 500K rows (MAX_ROWS in benchmark.py) - unlike
# the local benchmark.py script, which can go to 1M since it isn't
# constrained by the free-tier-Render request budget the live endpoint is.
SIZES = [10_000, 100_000, 500_000]
SIZE_LABELS = ["10K", "100K", "500K"]


def fetch_json(url: str, timeout: float = 60.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - operator-provided host
        return json.loads(resp.read())


def fetch_kernel_speedups(host: str) -> dict[str, list[float]]:
    speedup: dict[str, list[float]] = {KERNEL_LABELS[k]: [] for k in KERNEL_ORDER}
    for rows in SIZES:
        print(f"  GET /benchmark/kernels?rows={rows} ...")
        data = fetch_json(f"{host}/api/v1/benchmark/kernels?rows={rows}")
        if not data["cpp_available"]:
            print(f"ERROR: C++ extension not available on {host}.", file=sys.stderr)
            sys.exit(1)
        by_kernel = {r["kernel"]: r for r in data["results"]}
        for k in KERNEL_ORDER:
            speedup[KERNEL_LABELS[k]].append(by_kernel[k]["speedup"])
    return speedup


def fetch_parallel(host: str, rows: int, symbols: int) -> list[tuple[str, float]]:
    print(f"  GET /benchmark/parallel?rows={rows}&symbols={symbols} ...")
    data = fetch_json(f"{host}/api/v1/benchmark/parallel?rows={rows}&symbols={symbols}")
    if not data["cpp_available"]:
        print(f"ERROR: C++ extension not available on {host}.", file=sys.stderr)
        sys.exit(1)
    return [
        ("pandas\nsequential", data["pandas_sequential_ms"]),
        ("C++\nsequential", data["cpp_sequential_ms"]),
        (f"C++\n{symbols} threads", data["cpp_parallel_ms"]),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--parallel-rows", type=int, default=1_000_000)
    parser.add_argument("--parallel-symbols", type=int, default=8)
    parser.add_argument("--out", default="benchmark_chart_live")
    args = parser.parse_args()

    print(f"Fetching live numbers from {args.host} ...")
    speedup = fetch_kernel_speedups(args.host)
    parallel = fetch_parallel(args.host, args.parallel_rows, args.parallel_symbols)

    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    caption = (
        f"Live from {args.host} on {stamp} - median of repeated runs; identical "
        "synthetic OHLCV inputs; not a fixed hardware target, whatever this host "
        "is right now"
    )

    draw_benchmark_figure(
        speedup,
        SIZE_LABELS,
        parallel,
        caption,
        args.out,
        parallel_subtitle=f"{args.parallel_symbols} symbols × {args.parallel_rows:,} rows",
    )


if __name__ == "__main__":
    main()
