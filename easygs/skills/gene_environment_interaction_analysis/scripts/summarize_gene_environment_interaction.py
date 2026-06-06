#!/usr/bin/env python3
"""Summarize gene-by-environment interaction outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize GxE interaction outputs.")
    parser.add_argument("--vcf", required=True, help="Input VCF path.")
    parser.add_argument("--phenotype-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--env-csv", required=True, help="Input environment CSV path.")
    parser.add_argument("--output-dir", required=True, help="Analysis output directory.")
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
    output_dir = Path(args.output_dir)
    env_factor_dir = output_dir / "env_factors"
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    factor_files = sorted(env_factor_dir.glob("*_interactions.csv"))
    total_rows = 0
    non_empty_files = 0
    factor_counts: list[tuple[str, int]] = []
    best_row: dict[str, str] | None = None
    best_pvalue: float | None = None
    best_fvalue: float | None = None

    for factor_file in factor_files:
        row_count = 0
        with factor_file.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_count += 1
                pvalue = _safe_float(row.get("PValue"))
                fvalue = _safe_float(row.get("FValue"))
                if pvalue is None or fvalue is None:
                    continue
                if (
                    best_row is None
                    or best_pvalue is None
                    or pvalue < best_pvalue
                    or (pvalue == best_pvalue and best_fvalue is not None and fvalue > best_fvalue)
                ):
                    best_row = row
                    best_pvalue = pvalue
                    best_fvalue = fvalue
        total_rows += row_count
        if row_count > 0:
            non_empty_files += 1
        factor_counts.append((factor_file.name, row_count))

    lines = [
        "=== G与E互作分析 ===",
        f"输入 VCF: {Path(args.vcf)}",
        f"输入表型 CSV: {Path(args.phenotype_csv)}",
        f"输入环境因子 CSV: {Path(args.env_csv)}",
        "分析范围: 表型 CSV 中全部 TraitEnv 列",
        f"输出目录: {output_dir}",
        f"环境因子结果目录: {env_factor_dir}",
        f"环境因子文件数: {len(factor_files)}",
        f"非空结果文件数: {non_empty_files}",
        f"总互作记录数: {total_rows}",
    ]
    if best_row and best_pvalue is not None and best_fvalue is not None:
        lines.append(
            "最显著互作: "
            f"{best_row.get('Factor', 'n/a')} / {best_row.get('SNP', 'n/a')} "
            f"(Group={best_row.get('Group', 'n/a')}, "
            f"FValue={best_fvalue:.6f}, PValue={best_pvalue:.6g})"
        )
    if factor_counts:
        lines.append("结果文件记录数:")
        lines.extend(f"{name}: {count}" for name, count in factor_counts[:50])

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
