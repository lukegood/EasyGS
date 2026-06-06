#!/usr/bin/env python3
"""Summarize variance decomposition output."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize variance decomposition output.")
    parser.add_argument("--input-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--output-csv", required=True, help="Variance-component CSV path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    result_path = Path(args.output_csv)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    if result_path.exists():
        with result_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows = list(csv.DictReader(handle))

    lines = [
        "=== 方差分解分析 ===",
        f"输入表型 CSV: {input_path}",
        f"结果 CSV: {result_path}",
        f"方差分量行数: {len(rows)}",
    ]

    best_component = "n/a"
    best_percent: float | None = None
    for row in rows:
        component = row.get("component", "n/a")
        vcov = _safe_float(row.get("vcov"))
        percent = _safe_float(row.get("percent"))
        if vcov is None or percent is None:
            continue
        lines.append(f"{component}: vcov={vcov:.6f}, percent={percent:.6f}")
        if best_percent is None or percent > best_percent:
            best_percent = percent
            best_component = component

    if best_percent is not None:
        lines.append(f"最大方差占比: {best_component} ({best_percent:.6f}%)")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

