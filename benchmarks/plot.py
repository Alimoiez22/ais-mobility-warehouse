"""Regenerate every figure from the result files (no database needed).

Usage: uv run python benchmarks/plot.py

  docs/figures/cleaning.png   rows removed by each cleaning rule (RQ1)
  docs/figures/benchmark.png  median latency with IQR per query and index type (RQ3)
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "docs" / "figures"
COLORS = {"none": "#8c8c8c", "gist": "#2f6fb0", "spgist": "#d9822b"}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def style(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#e5e5e5", linewidth=0.8)
    ax.set_axisbelow(True)


def cleaning_figure() -> None:
    rows = [r for r in read(RESULTS / "cleaning.csv") if r["step"] != "0"]
    labels = [r["rule"].replace("_", " ") for r in rows]
    removed = [int(r["rows_removed"]) for r in rows]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bars = ax.barh(labels[::-1], [v / 1e6 for v in removed[::-1]], color="#2f6fb0")
    for bar, r in zip(bars, rows[::-1]):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f"  {int(r['rows_removed']):,} ({r['pct_of_raw']}% of raw)", va="center", fontsize=9)
    ax.set_xlabel("Rows removed (millions)")
    raw = int(read(RESULTS / "cleaning.csv")[0]["rows_before"])
    kept = int(rows[-1]["rows_after"])
    ax.set_title(f"Cleaning rules, in order: {raw:,} raw rows to {kept:,} kept", loc="left", fontsize=11)
    ax.set_xlim(0, max(removed) / 1e6 * 1.6)
    style(ax)
    fig.tight_layout()
    fig.savefig(FIGURES / "cleaning.png", dpi=150)
    plt.close(fig)


def benchmark_figure() -> None:
    rows = read(RESULTS / "bench" / "summary.csv")
    queries = list(dict.fromkeys(r["query"] for r in rows))
    configs = list(dict.fromkeys(r["config"] for r in rows))
    fig, ax = plt.subplots(figsize=(8, 4))
    height = 0.8 / len(configs)
    for i, config in enumerate(configs):
        data = {r["query"]: r for r in rows if r["config"] == config}
        ys = [q + (i - (len(configs) - 1) / 2) * height for q in range(len(queries))]
        med = [float(data[q]["median_ms"]) for q in queries]
        lo = [float(data[q]["median_ms"]) - float(data[q]["q1_ms"]) for q in queries]
        hi = [float(data[q]["q3_ms"]) - float(data[q]["median_ms"]) for q in queries]
        ax.barh(ys, med, height=height * 0.9, color=COLORS.get(config, "#555"), label=config,
                xerr=[lo, hi], error_kw={"elinewidth": 1, "capsize": 2})
    ax.set_yticks(range(len(queries)), [q.replace("_", " ") for q in queries])
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("Median execution time, ms (log scale; whiskers = IQR, 5 warm runs)")
    ax.set_title("Spatial index benchmark on dw.fact_position", loc="left", fontsize=11)
    ax.legend(title="Index", frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    style(ax)
    fig.tight_layout()
    fig.savefig(FIGURES / "benchmark.png", dpi=150)
    plt.close(fig)


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    cleaning_figure()
    print("Wrote docs/figures/cleaning.png")
    if (RESULTS / "bench" / "summary.csv").exists():
        benchmark_figure()
        print("Wrote docs/figures/benchmark.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
