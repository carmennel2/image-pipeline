"""Plot a scaling-test run as a chart.

Reads a run CSV from run_scaling_test.py and draws the backlog and the
processing throughput over time, saving the chart as a PNG beside the CSV.

Usage:
  python evaluation/plot_run.py [path-to-run-csv]   (defaults to the latest run)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BACKLOG_COLOR = "#1A5C86"
THROUGHPUT_COLOR = "#E8821E"


def _load(csv_path: Path) -> tuple[list[float], list[int], list[int]]:
    """Read elapsed time, completed count, and backlog from a run CSV."""
    elapsed: list[float] = []
    completed: list[int] = []
    backlog: list[int] = []
    with csv_path.open() as handle:
        for row in csv.DictReader(handle):
            elapsed.append(float(row["elapsed_seconds"]))
            completed.append(int(row["completed"]))
            backlog.append(int(row["backlog"]))
    return elapsed, completed, backlog


def _throughput(elapsed: list[float], completed: list[int]):
    """Return (times, rates) where rate is images completed per second."""
    times: list[float] = []
    rates: list[float] = []
    for i in range(1, len(elapsed)):
        dt = elapsed[i] - elapsed[i - 1]
        if dt > 0:
            times.append(elapsed[i])
            rates.append((completed[i] - completed[i - 1]) / dt)
    return times, rates


def main() -> None:
    """Plot the most recent run CSV (or the one given as an argument)."""
    folder = Path(__file__).resolve().parent
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        runs = sorted(folder.glob("run_*.csv"))
        if not runs:
            raise SystemExit("No run CSV found.")
        csv_path = runs[-1]

    elapsed, completed, backlog = _load(csv_path)
    total = max(completed) if completed else 0
    thr_t, thr = _throughput(elapsed, completed)

    proc_start = next(
        (elapsed[i] for i in range(len(completed)) if completed[i] > 0), 0.0
    )
    proc_time = elapsed[-1] - proc_start
    avg_rate = total / proc_time if proc_time else 0.0

    fig, ax1 = plt.subplots(figsize=(10, 5.6))

    ax1.fill_between(elapsed, backlog, color=BACKLOG_COLOR, alpha=0.16)
    ax1.plot(elapsed, backlog, color=BACKLOG_COLOR, linewidth=2.3,
             label="Images remaining to process")
    ax1.set_xlabel("Elapsed time (seconds)", fontsize=11)
    ax1.set_ylabel("Images remaining", color=BACKLOG_COLOR, fontsize=11)
    ax1.tick_params(axis="y", labelcolor=BACKLOG_COLOR)
    ax1.set_ylim(0, total * 1.06)
    ax1.set_xlim(0, elapsed[-1])
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(thr_t, thr, color=THROUGHPUT_COLOR, linewidth=2.3,
             label="Processing throughput")
    ax2.set_ylabel("Throughput (images / second)", color=THROUGHPUT_COLOR, fontsize=11)
    ax2.tick_params(axis="y", labelcolor=THROUGHPUT_COLOR)
    ax2.set_ylim(0, (max(thr) if thr else 1) * 1.3)

    ax1.axvline(proc_start, color="#8A95A3", linestyle="--", linewidth=1.1)
    ax1.annotate("processing begins", xy=(proc_start, total * 0.55),
                 xytext=(proc_start + 10, total * 0.55),
                 fontsize=9, color="#555555")

    fig.suptitle(f"Scaling Test: Processing a {total:,}-Image Batch",
                 fontsize=14, fontweight="bold", y=0.99)
    ax1.set_title(
        f"{total:,} images processed in {proc_time:.0f} seconds   |   "
        f"sustained throughput {avg_rate:.0f} images per second",
        fontsize=10, color="#555555", pad=8)

    lines = ax1.get_lines()[:1] + ax2.get_lines()[:1]
    ax1.legend(lines, [ln.get_label() for ln in lines],
               loc="center right", fontsize=9, framealpha=0.95)

    fig.tight_layout()
    png_path = csv_path.with_suffix(".png")
    fig.savefig(png_path, dpi=150)
    print(f"Saved chart to {png_path}")
    print(f"  total images: {total}")
    print(f"  processing time: {proc_time:.0f} s")
    print(f"  sustained throughput: {avg_rate:.1f} images/s")


if __name__ == "__main__":
    main()
