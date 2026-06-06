#!/usr/bin/env python3
"""Summarize gene-by-gene interaction outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize gene-by-gene interaction outputs.")
    parser.add_argument("--vcf", required=True, help="Input VCF path.")
    parser.add_argument("--phenotype-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--gene-map", required=True, help="Input gene-map path.")
    parser.add_argument("--output-dir", required=True, help="Analysis output directory.")
    parser.add_argument("--summary-csv", required=True, help="Gene interaction summary CSV path.")
    parser.add_argument("--detail-csv", required=True, help="Detailed SNP-pair CSV path.")
    parser.add_argument("--report-path", required=True, help="Analysis report path.")
    parser.add_argument("--threshold", required=True, help="FDR threshold used in the run.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    summary_csv_path = Path(args.summary_csv)
    detail_csv_path = Path(args.detail_csv)
    report_path = Path(args.report_path)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    summary_df = _read_csv(summary_csv_path)
    detail_df = _read_csv(detail_csv_path)

    lines = [
        "=== Gene-by-gene interaction analysis ===",
        f"Input VCF: {Path(args.vcf)}",
        f"Input phenotype CSV: {Path(args.phenotype_csv)}",
        f"Input gene-map file: {Path(args.gene_map)}",
        f"FDR threshold: {args.threshold}",
        f"Output directory: {output_dir}",
        f"Summary CSV: {summary_csv_path}",
        f"Detailed SNP-pair CSV: {detail_csv_path}",
        f"Analysis report: {report_path}",
        f"Significant gene pairs: {len(summary_df)}",
        f"Significant SNP pairs: {len(detail_df)}",
    ]

    if not summary_df.empty and {"Gene1", "Gene2", "Avg_FDR", "Avg_F_value", "Avg_P_value", "Num_Significant_Pairs"}.issubset(
        summary_df.columns
    ):
        top_row = summary_df.sort_values(["Avg_FDR", "Avg_P_value"], ascending=[True, True]).iloc[0]
        lines.append(
            "Top gene pair: "
            f"{top_row['Gene1']} x {top_row['Gene2']} "
            f"(Avg_FDR={float(top_row['Avg_FDR']):.6g}, "
            f"Avg_F={float(top_row['Avg_F_value']):.6g}, "
            f"Significant SNP pairs={int(top_row['Num_Significant_Pairs'])})"
        )

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
