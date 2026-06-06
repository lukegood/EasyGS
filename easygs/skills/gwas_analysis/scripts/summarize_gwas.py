#!/usr/bin/env python3
"""Summarize rMVP GWAS outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize rMVP GWAS outputs.")
    parser.add_argument("--bfile-prefix", required=True, help="Input BFILE prefix.")
    parser.add_argument("--phenotype-csv", required=True, help="Input phenotype CSV.")
    parser.add_argument("--output-dir", required=True, help="GWAS output directory.")
    parser.add_argument("--summary-output", required=True, help="Summary output path.")
    parser.add_argument("--trait-column", required=True, help="Trait column / output prefix.")
    parser.add_argument("--methods", required=True, help="Comma-separated GWAS methods.")
    return parser.parse_args()


def _count_rows(path: Path) -> int:
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
    output_dir = Path(args.output_dir)
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    prefix = args.trait_column
    lines = [
        "=== GWAS 分析 ===",
        f"BFILE prefix: {args.bfile_prefix}",
        f"Phenotype CSV: {args.phenotype_csv}",
        f"Output dir: {output_dir}",
        f"Trait prefix: {prefix}",
        f"Methods: {', '.join(methods)}",
    ]

    for label, desc_name in (
        ("MVP genotype prefix", "mvp.plink.geno.desc"),
        ("Kinship prefix", "mvpKin.kin.desc"),
        ("PC prefix", "mvpPC.pc.desc"),
    ):
        path = output_dir / desc_name
        if path.exists():
            lines.append(f"{label}: {path.name}")

    generated = sorted(
        path.name
        for path in output_dir.iterdir()
        if path.is_file()
        and path.name.startswith(f"{prefix}.")
        and not path.name.endswith("_gwas_summary.txt")
    ) if output_dir.exists() else []

    lines.append(f"Generated result files: {len(generated)}")

    for method in methods:
        full_csv = output_dir / f"{prefix}.{method}.csv"
        signal_csv = output_dir / f"{prefix}.{method}_signals.csv"
        full_rows = _count_rows(full_csv)
        signal_rows = _count_rows(signal_csv)
        lines.append(f"{method} full-result rows: {full_rows}")
        lines.append(f"{method} signal rows: {signal_rows}")
        for suffix in (
            f"{method}.csv",
            f"{method}_signals.csv",
            f"{method}.QQplot.jpg",
            f"{method}.Circular-Manhattan.jpg",
            f"{method}.Rectangular-Manhattan.jpg",
        ):
            path = output_dir / f"{prefix}.{suffix}"
            if path.exists():
                lines.append(f"{method} file: {path.name}")

    for extra_name in (
        f"{prefix}.PCA_2D.jpg",
        f"{prefix}.Phe_Dist.jpg",
        f"{prefix}.FarmCPU.SNP-Density.jpg",
        f"{prefix}.MLM.SNP-Density.jpg",
        f"{prefix}.GLM.SNP-Density.jpg",
    ):
        path = output_dir / extra_name
        if path.exists():
            lines.append(f"Extra file: {path.name}")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
