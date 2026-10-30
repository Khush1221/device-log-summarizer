#!/usr/bin/env python3
"""Section 3: bar chart of average temperature per device from summary.json."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe: write to file, never open a window
import matplotlib.pyplot as plt  # noqa: E402

DEFAULT_INPUT = "output/summary.json"
DEFAULT_OUTPUT = "output/temperature_chart.png"


def load_summary(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(f"Error: {path} not found. Run summarizer.py first.")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Error: {path} is not valid JSON ({exc}).")
    if not data.get("devices"):
        raise SystemExit("Error: no devices in the summary - nothing to plot.")
    return data


def plot(data: dict, output: Path) -> None:
    devices = data["devices"]
    names = [d["device_id"] for d in devices]
    temps = [d["avg_temperature"] for d in devices]
    threshold = data.get("temperature_threshold")

    fig, ax = plt.subplots(figsize=(max(6.0, 1.1 * len(names) + 2), 5.5))
    bars = ax.bar(names, temps, color="#4C78A8", edgecolor="black", linewidth=0.6)

    # Value label above each bar
    for bar, value in zip(bars, temps):
        ax.annotate(f"{value:.2f}", (bar.get_x() + bar.get_width() / 2, value),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9)

    if threshold is not None:
        ax.axhline(threshold, color="#D62728", linestyle="--", linewidth=1.2,
                   label=f"Threshold ({threshold:g} °C)")
        ax.legend(loc="upper right")

    top = max(temps + [threshold or 0])
    ax.set_ylim(0, top * 1.15)  # headroom so labels / legend never clip
    ax.set_title("Average Temperature per Device", fontsize=14, fontweight="bold")
    ax.set_xlabel("Device ID")
    ax.set_ylabel("Average temperature (°C)")
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    if len(names) > 8:  # avoid overlapping tick labels with many devices
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Plot average temperature per device.")
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    plot(load_summary(Path(args.input)), Path(args.output))
    print(f"Chart saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
