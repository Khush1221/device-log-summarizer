#!/usr/bin/env python3
"""Device Log Summarizer CLI (Section 2).

Reads device telemetry CSV, aggregates per device, filters out devices that run
too hot, prints a summary table and exports the result as JSON.
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

REQUIRED_COLUMNS = ("device_id", "status", "temperature")
VALID_STATUSES = ("ACTIVE", "WARNING", "ERROR")
DEFAULT_THRESHOLD = 80.0
DEFAULT_INPUT = "data/device_telemetry.csv"
DEFAULT_OUTPUT = "output/summary.json"


class TelemetryError(Exception):
    """Fatal, user-facing problem (missing file, wrong columns, no usable data)."""


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
def read_telemetry(path: Path) -> Tuple[List[dict], List[Tuple[int, str]]]:
    """Read the CSV. Returns (valid_records, skipped) where skipped holds
    (line_number, reason) for every row that could not be used."""
    if not path.exists():
        raise TelemetryError(f"Input file not found: {path}")
    if not path.is_file():
        raise TelemetryError(f"Input path is not a file: {path}")

    records: List[dict] = []
    skipped: List[Tuple[int, str]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise TelemetryError(f"Input file is empty: {path}")
            reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]
            missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise TelemetryError(f"Missing required column(s): {', '.join(missing)}")

            for row in reader:
                line = reader.line_num
                device_id = (row.get("device_id") or "").strip()
                status = (row.get("status") or "").strip().upper()
                temp_raw = (row.get("temperature") or "").strip()

                if not device_id:
                    skipped.append((line, "missing device_id"))
                    continue
                if status not in VALID_STATUSES:
                    skipped.append((line, f"invalid status {row.get('status')!r}"))
                    continue
                try:
                    temperature = float(temp_raw)
                except ValueError:
                    skipped.append((line, f"invalid temperature {temp_raw!r}"))
                    continue
                if not math.isfinite(temperature):
                    skipped.append((line, f"non-finite temperature {temp_raw!r}"))
                    continue
                records.append({"device_id": device_id, "status": status, "temperature": temperature})
    except UnicodeDecodeError as exc:
        raise TelemetryError(f"Could not decode {path} as UTF-8: {exc}") from exc
    except (OSError, csv.Error) as exc:
        raise TelemetryError(f"Could not read {path}: {exc}") from exc

    return records, skipped


# --------------------------------------------------------------------------- #
# Processing
# --------------------------------------------------------------------------- #
def aggregate(records: List[dict]) -> Dict[str, dict]:
    """Group by device_id -> total records, mean temperature, ERROR count."""
    totals = defaultdict(lambda: {"count": 0, "temp_sum": 0.0, "errors": 0})
    for rec in records:
        bucket = totals[rec["device_id"]]
        bucket["count"] += 1
        bucket["temp_sum"] += rec["temperature"]
        if rec["status"] == "ERROR":
            bucket["errors"] += 1

    return {
        device: {
            "device_id": device,
            "total_records": b["count"],
            "avg_temperature": round(b["temp_sum"] / b["count"], 2),
            "error_count": b["errors"],
        }
        for device, b in totals.items()
    }


def filter_hot_devices(stats: Dict[str, dict], threshold: float) -> Tuple[List[dict], List[dict]]:
    """Split devices into (kept, excluded). Excluded = average temp above threshold."""
    kept = sorted((s for s in stats.values() if s["avg_temperature"] <= threshold),
                  key=lambda s: s["device_id"])
    excluded = sorted((s for s in stats.values() if s["avg_temperature"] > threshold),
                      key=lambda s: s["device_id"])
    return kept, excluded


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def print_table(devices: List[dict]) -> None:
    headers = ("Device", "Records", "Avg Temp (C)", "Errors")
    rows = [(d["device_id"], str(d["total_records"]), f"{d['avg_temperature']:.2f}",
             str(d["error_count"])) for d in devices]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(headers)]
    line = "+-" + "-+-".join("-" * w for w in widths) + "-+"

    def fmt(cells):
        out = [cells[0].ljust(widths[0])] + [c.rjust(w) for c, w in zip(cells[1:], widths[1:])]
        return "| " + " | ".join(out) + " |"

    print(line)
    print(fmt(headers))
    print(line)
    for r in rows:
        print(fmt(r))
    print(line)


def export_json(path: Path, kept, excluded, threshold, source, rows_read, skipped) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(source),
        "temperature_threshold": threshold,
        "rows_read": rows_read,
        "rows_skipped": len(skipped),
        "devices": kept,
        "excluded_devices": [
            {"device_id": d["device_id"], "avg_temperature": d["avg_temperature"]} for d in excluded
        ],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise TelemetryError(f"Could not write {path}: {exc}") from exc


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Summarize device telemetry from a CSV file.")
    p.add_argument("input", nargs="?", default=DEFAULT_INPUT, help=f"CSV file (default: {DEFAULT_INPUT})")
    p.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help=f"JSON output (default: {DEFAULT_OUTPUT})")
    p.add_argument("-t", "--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help="Exclude devices whose average temperature is above this (default: 80.0)")
    p.add_argument("-v", "--verbose", action="store_true", help="List every skipped row")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    source, destination = Path(args.input), Path(args.output)
    try:
        records, skipped = read_telemetry(source)
        if not records:
            raise TelemetryError("No valid records found in the input file.")
        stats = aggregate(records)
        kept, excluded = filter_hot_devices(stats, args.threshold)
        export_json(destination, kept, excluded, args.threshold, source,
                    len(records) + len(skipped), skipped)
    except TelemetryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"\nDevice Summary (avg temperature <= {args.threshold:g} C)")
    print_table(kept)
    print(f"\nRows read: {len(records) + len(skipped)} | skipped: {len(skipped)} | "
          f"devices kept: {len(kept)} | excluded (too hot): {len(excluded)}")
    for d in excluded:
        print(f"  excluded {d['device_id']}: avg {d['avg_temperature']:.2f} C")
    if skipped:
        print(f"Warning: {len(skipped)} invalid row(s) skipped"
              + ("" if args.verbose else " (use --verbose for details)"), file=sys.stderr)
        if args.verbose:
            for line, reason in skipped:
                print(f"  line {line}: {reason}", file=sys.stderr)
    print(f"Saved results to {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
