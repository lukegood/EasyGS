#!/usr/bin/env python3
"""Summarize reaction norm outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize reaction norm outputs.")
    parser.add_argument("--input-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--long-output", required=True, help="Long-format phenotype CSV path.")
    parser.add_argument("--slope-output", required=True, help="Intercept/slope CSV path.")
    parser.add_argument("--trait-label", required=True, help="Trait label used in the run.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def main() -> None:
    args = parse_args()
    long_output = Path(args.long_output)
    slope_output = Path(args.slope_output)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    long_rows = _count_csv_rows(long_output)
    slope_rows = 0
    best_line = "n/a"
    best_slope: float | None = None

    if slope_output.exists():
        with slope_output.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                slope_rows += 1
                slope_value = _safe_float(row.get("slope"))
                if slope_value is None:
                    continue
                if best_slope is None or slope_value > best_slope:
                    best_slope = slope_value
                    best_line = row.get("LINE", "n/a")

    lines = [
        "=== 反应范式计算分析 ===",
        f"输入表型 CSV: {Path(args.input_csv)}",
        f"性状标签: {args.trait_label}",
        f"长格式表型 CSV: {long_output}",
        f"截距斜率 CSV: {slope_output}",
        f"长格式记录数: {long_rows}",
        f"截距斜率记录数: {slope_rows}",
    ]
    if best_slope is not None:
        lines.append(f"最高斜率材料: {best_line} (slope={best_slope:.6f})")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
