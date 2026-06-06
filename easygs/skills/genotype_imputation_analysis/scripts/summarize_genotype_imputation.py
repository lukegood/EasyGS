#!/usr/bin/env python3
"""Summarize Beagle genotype-imputation outputs."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Beagle genotype-imputation outputs.")
    parser.add_argument("--input-vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--jar", required=True, help="Beagle jar path.")
    parser.add_argument("--output-prefix", required=True, help="Beagle output prefix.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _count_variants(path: Path) -> str:
    if not path.exists():
        return "n/a"
    opener = gzip.open if str(path).endswith(".gz") else open
    count = 0
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line and not line.startswith("#"):
                count += 1
    return str(count)


def main() -> None:
    args = parse_args()
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    output_prefix = Path(args.output_prefix)
    output_vcf_gz = output_prefix.parent / f"{output_prefix.name}.vcf.gz"
    output_log = output_prefix.parent / f"{output_prefix.name}.log"
    input_vcf = Path(args.input_vcf)

    lines = [
        "Genotype imputation summary",
        f"Input VCF: {input_vcf}",
        f"Beagle jar: {Path(args.jar)}",
        f"Output prefix: {output_prefix}",
        f"Input variant count: {_count_variants(input_vcf)}",
        f"Output variant count: {_count_variants(output_vcf_gz)}",
        "",
        "Generated files:",
        f"- {output_vcf_gz}",
        f"- {output_log}",
    ]

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
