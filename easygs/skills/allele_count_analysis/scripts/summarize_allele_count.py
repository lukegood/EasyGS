#!/usr/bin/env python3
"""Summarize vcftools allele-count output."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize vcftools allele-count output.")
    parser.add_argument("--input-vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--count", required=True, help="vcftools .frq.count output path.")
    parser.add_argument("--log", required=True, help="vcftools .log output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_count_token(token: str) -> int | None:
    if ":" not in token:
        return None
    _, value = token.split(":", 1)
    if value in {".", "nan", "NaN"}:
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except ValueError:
            return None


def main() -> None:
    args = parse_args()
    count_path = Path(args.count)
    log_path = Path(args.log)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [line.strip() for line in count_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    data_rows = rows[1:] if rows else []

    total_sites = 0
    polymorphic_sites = 0
    minor_allele_counts: list[int] = []

    for line in data_rows:
        parts = line.split()
        if len(parts) < 5:
            continue
        total_sites += 1
        counts = [count for count in (_parse_count_token(token) for token in parts[4:]) if count is not None and count > 0]
        if len(counts) >= 2:
            polymorphic_sites += 1
            minor_allele_counts.append(min(counts))

    proportion = (polymorphic_sites / total_sites) if total_sites else 0.0
    mean_minor_count = statistics.mean(minor_allele_counts) if minor_allele_counts else 0.0

    lines = [
        "Allele count summary",
        f"Input VCF: {Path(args.input_vcf)}",
        f"Count file: {count_path}",
        f"vcftools log: {log_path}",
        f"Total site count: {total_sites}",
        f"Polymorphic site count: {polymorphic_sites}",
        f"Polymorphic site proportion: {proportion:.6f}",
        f"Mean counted minor allele count (polymorphic sites): {mean_minor_count:.6f}",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
