#!/usr/bin/env python3
"""Summarize filtered PLINK outputs."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bed-prefix", required=True)
    parser.add_argument("--vcf-gz", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mind", required=True)
    parser.add_argument("--geno", required=True)
    parser.add_argument("--hwe", required=True)
    parser.add_argument("--maf", required=True)
    return parser.parse_args()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def count_vcf_records(path: Path) -> int:
    if not path.exists():
        return 0
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        return sum(1 for line in handle if line and not line.startswith("#"))


def main() -> None:
    args = parse_args()
    bed_prefix = Path(args.bed_prefix)
    vcf_gz = Path(args.vcf_gz)
    output = Path(args.output)

    sample_count = count_lines(bed_prefix.with_suffix(".fam"))
    variant_count = count_lines(bed_prefix.with_suffix(".bim"))
    exported_vcf_records = count_vcf_records(vcf_gz)

    lines = [
        "PLINK filter summary",
        f"BED prefix: {bed_prefix}",
        f"Filtered VCF.GZ: {vcf_gz}",
        f"Sample count after filtering: {sample_count}",
        f"Variant count after filtering (.bim): {variant_count}",
        f"Variant count in filtered VCF.GZ: {exported_vcf_records}",
        f"Applied thresholds: mind={args.mind}, geno={args.geno}, hwe={args.hwe}, maf={args.maf}",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
