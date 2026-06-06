#!/usr/bin/env python3
"""Summarize combining ability outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize combining ability outputs.")
    parser.add_argument("--input-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--female-gca-output", required=True, help="Female GCA CSV path.")
    parser.add_argument("--male-gca-output", required=True, help="Male GCA CSV path.")
    parser.add_argument("--sca-output", required=True, help="SCA CSV path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_best(path: Path, value_column: str) -> tuple[int, str, float | None]:
    if not path.exists():
        return 0, "n/a", None

    count = 0
    best_label = "n/a"
    best_value: float | None = None
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        id_columns = [name for name in (reader.fieldnames or []) if name != value_column]
        id_column = id_columns[0] if id_columns else ""
        for row in reader:
            count += 1
            value = _safe_float(row.get(value_column))
            if value is None:
                continue
            if best_value is None or value > best_value:
                best_value = value
                best_label = row.get(id_column, "n/a") if id_column else "n/a"
    return count, best_label, best_value


def main() -> None:
    args = parse_args()
    female_path = Path(args.female_gca_output)
    male_path = Path(args.male_gca_output)
    sca_path = Path(args.sca_output)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    female_count, best_female, best_female_value = _read_best(female_path, "GCA")
    male_count, best_male, best_male_value = _read_best(male_path, "GCA")
    sca_count, best_hybrid, best_sca_value = _read_best(sca_path, "SCA")

    lines = [
        "=== 配合力计算分析 ===",
        f"输入表型 CSV: {Path(args.input_csv)}",
        f"Female GCA CSV: {female_path}",
        f"Male GCA CSV: {male_path}",
        f"SCA CSV: {sca_path}",
        f"Female GCA 行数: {female_count}",
        f"Male GCA 行数: {male_count}",
        f"SCA 行数: {sca_count}",
    ]
    if best_female_value is not None:
        lines.append(f"最高 Female GCA: {best_female} (GCA={best_female_value:.6f})")
    if best_male_value is not None:
        lines.append(f"最高 Male GCA: {best_male} (GCA={best_male_value:.6f})")
    if best_sca_value is not None:
        lines.append(f"最高 SCA 组合: {best_hybrid} (SCA={best_sca_value:.6f})")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
