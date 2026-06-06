#!/usr/bin/env python3
"""Summarize vcftools allele-frequency output."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize vcftools allele-frequency output.")
    parser.add_argument("--input-vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--frq", required=True, help="vcftools .frq output path.")
    parser.add_argument("--log", required=True, help="vcftools .log output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_freq_token(token: str) -> float | None:
    if ":" not in token:
        return None
    _, value = token.split(":", 1)
    if value in {".", "nan", "NaN"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    frq_path = Path(args.frq)
    log_path = Path(args.log)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [line.strip() for line in frq_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    data_rows = rows[1:] if rows else []

    total_sites = 0
    polymorphic_sites = 0
    minor_allele_freqs: list[float] = []

    for line in data_rows:
        parts = line.split()
        if len(parts) < 5:
            continue
        total_sites += 1
        freqs = [freq for freq in (_parse_freq_token(token) for token in parts[4:]) if freq is not None and freq > 0]
        if len(freqs) >= 2:
            polymorphic_sites += 1
            minor_allele_freqs.append(min(freqs))

    proportion = (polymorphic_sites / total_sites) if total_sites else 0.0
    mean_maf = statistics.mean(minor_allele_freqs) if minor_allele_freqs else 0.0

    lines = [
        "Allele frequency summary",
        f"Input VCF: {Path(args.input_vcf)}",
        f"Frequency file: {frq_path}",
        f"vcftools log: {log_path}",
        f"Total site count: {total_sites}",
        f"Polymorphic site count: {polymorphic_sites}",
        f"Polymorphic site proportion: {proportion:.6f}",
        f"Mean minor allele frequency (polymorphic sites): {mean_maf:.6f}",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
