#!/usr/bin/env python3
"""Summarize CERIS-style environment index outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize environment index outputs.")
    parser.add_argument("--env-meta", required=True, help="Input Env_meta_table.txt path.")
    parser.add_argument("--trait-records", required=True, help="Input Trait_records.txt path.")
    parser.add_argument("--env-paras", required=True, help="Input environment-parameter table path.")
    parser.add_argument("--output-dir", required=True, help="Analysis output directory.")
    parser.add_argument("--trait-label", required=True, help="Trait label used for the output directory.")
    parser.add_argument("--trait-column", required=True, help="Trait column analyzed from Trait_records.txt.")
    parser.add_argument("--run-downstream", required=True, help="Whether downstream plot/slope/LOO steps were requested.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def count_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def read_best_row(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        return next(reader, None)


def list_trait_outputs(path: Path) -> list[str]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted(item.name for item in path.iterdir() if item.is_file())


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    trait_dir = output_dir / args.trait_label
    allwinds_path = output_dir / "allwinds_EF_cor.csv"
    highest_path = output_dir / "highest_EF.csv"
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    allwinds_rows = count_data_rows(allwinds_path) if allwinds_path.exists() else 0
    highest_rows = count_data_rows(highest_path) if highest_path.exists() else 0
    trait_outputs = list_trait_outputs(trait_dir)
    best_row = read_best_row(highest_path)

    lines = [
        "=== 环境指数计算分析 ===",
        f"输入 Env meta: {Path(args.env_meta)}",
        f"输入 Trait records: {Path(args.trait_records)}",
        f"输入 Env paras: {Path(args.env_paras)}",
        f"分析性状列: {args.trait_column}",
        f"执行下游绘图/斜率/LOO: {args.run_downstream}",
        f"输出目录: {output_dir}",
        f"性状结果目录: {trait_dir}",
        f"allwinds_EF_cor.csv: {allwinds_path}",
        f"allwinds 记录数: {allwinds_rows}",
        f"highest_EF.csv: {highest_path}",
        f"highest 记录数: {highest_rows}",
        f"性状目录文件数: {len(trait_outputs)}",
    ]
    if best_row:
        lines.append(
            "最高相关环境因子: "
            f"{best_row.get('Parameter', 'n/a')} "
            f"(Day_x={best_row.get('Day_x', 'n/a')}, "
            f"Day_y={best_row.get('Day_y', 'n/a')}, "
            f"Corr={best_row.get('Corr', 'n/a')})"
        )
    if trait_outputs:
        lines.append("性状目录文件:")
        lines.extend(trait_outputs[:20])

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
