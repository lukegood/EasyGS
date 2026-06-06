#!/usr/bin/env python3
"""Summarize phenotype BLUP outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize phenotype BLUP outputs.")
    parser.add_argument("--input-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--output-csv", required=True, help="BLUP CSV output path.")
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
    output_csv = Path(args.output_csv)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    best_line = "n/a"
    best_value: float | None = None

    if output_csv.exists():
        with output_csv.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                total_rows += 1
                value = _safe_float(row.get("BLUP_Value"))
                if value is None:
                    continue
                if best_value is None or value > best_value:
                    best_value = value
                    best_line = row.get("LINE_ID", "n/a")

    lines = [
        "=== 表型BLUP计算分析 ===",
        f"输入表型 CSV: {Path(args.input_csv)}",
        f"输出 BLUP CSV: {output_csv}",
        f"BLUP 行数: {total_rows}",
    ]
    if best_value is not None:
        lines.append(f"最高 BLUP 材料: {best_line} (BLUP={best_value:.6f})")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
