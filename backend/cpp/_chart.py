"""
AEQUITAS - Shared drawing code for the benchmark figure.

Used by both make_benchmark_chart.py (hardcoded numbers you paste in
after a local run) and make_live_benchmark_chart.py (numbers fetched live
from a running API host). Kept as one function so the two charts never
drift apart in styling.
"""

import matplotlib.pyplot as plt
import numpy as np

INK = "#1a1a2e"
BLUES = ["#a8c5e8", "#5b8bc9", "#1f4e8c"]
GREEN = "#2e7d52"


def draw_benchmark_figure(
    speedup: dict[str, list[float]],
    size_labels: list[str],
    parallel: list[tuple[str, float]],
    caption: str,
    out_prefix: str,
    parallel_subtitle: str = "multi-symbol",
) -> None:
    """
    speedup: kernel label -> [speedup @ size_labels[0], @ size_labels[1], ...]
    parallel: [(bar label, wall-clock ms), ...] - pandas seq, C++ seq, C++ parallel
    caption: footer text (hardware, methodology)
    out_prefix: writes "{out_prefix}.png" and "{out_prefix}.svg"
    """
    kernels = list(speedup.keys())

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.7, 1]}
    )
    fig.patch.set_facecolor("white")

    # -- Panel 1: per-kernel speedup by dataset size --------------
    x = np.arange(len(kernels))
    w = 0.26
    for i, size in enumerate(size_labels):
        vals = [speedup[k][i] for k in kernels]
        bars = ax1.bar(x + (i - 1) * w, vals, w, label=f"{size} rows", color=BLUES[i])
        for b, v in zip(bars, vals, strict=False):
            yoff = 1.06 if i != 1 else 1.22  # stagger to avoid label collisions
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
    ax1.text(len(kernels) - 0.45, 1.08, "parity", fontsize=7.5, color="#777")
    ax1.set_yscale("log")
    ax1.set_ylim(0.8, 90)
    ax1.set_yticks([1, 2, 5, 10, 20, 40, 80])
    ax1.set_yticklabels(["1x", "2x", "5x", "10x", "20x", "40x", "80x"])
    ax1.set_xticks(x)
    ax1.set_xticklabels(kernels, fontsize=8.5)
    ax1.set_ylabel("speedup vs pandas (log scale)", fontsize=9)
    ax1.set_title(
        "C++20 kernel speedup vs pandas, by dataset size", fontsize=10, color=INK
    )
    ax1.legend(fontsize=8, frameon=False)
    ax1.spines[["top", "right"]].set_visible(False)

    # -- Panel 2: multi-symbol parallel (the GIL-release payoff) --
    labels = [p[0] for p in parallel]
    times = [p[1] for p in parallel]
    colors = ["#b0b0b0", BLUES[2], GREEN]
    bars = ax2.bar(labels, times, 0.6, color=colors[: len(times)])
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
    end_to_end_speedup = times[0] / times[-1] if times[-1] > 0 else 0
    ax2.text(
        2,
        times[0] * 0.55,
        f"{end_to_end_speedup:.1f}x\nend-to-end",
        ha="center",
        fontsize=9,
        color=GREEN,
        fontweight="bold",
    )
    ax2.set_yscale("log")
    ax2.set_ylim(min(times) * 0.5, max(times) * 3)
    ax2.set_ylabel("wall clock, ms (log scale)", fontsize=9)
    ax2.set_title(
        f"RSI-14, {parallel_subtitle}\n(ThreadPoolExecutor + GIL release)",
        fontsize=10,
        color=INK,
    )
    ax2.spines[["top", "right"]].set_visible(False)

    fig.text(0.5, -0.04, caption, ha="center", fontsize=7.5, color="#666")

    plt.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(
            f"{out_prefix}.{ext}", dpi=300, bbox_inches="tight", facecolor="white"
        )
    print(f"wrote {out_prefix}.png and {out_prefix}.svg")
