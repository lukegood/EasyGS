#!/usr/bin/env python3
"""Summarize vcftools Tajima's D output."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize vcftools Tajima's D output.")
    parser.add_argument("--input-vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--window-size", type=int, required=True, help="Window size used for vcftools --TajimaD.")
    parser.add_argument("--result", required=True, help="vcftools .Tajima.D output path.")
    parser.add_argument("--log", required=True, help="vcftools .log output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_float(token: str) -> float | None:
    if token in {".", "nan", "NaN", "inf", "-inf"}:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    result_path = Path(args.result)
    log_path = Path(args.log)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        line.strip()
        for line in result_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]

    total_rows = 0
    values: list[float] = []

    for line in rows[1:] if rows else []:
        parts = line.split()
        if len(parts) < 2:
            continue
        total_rows += 1
        value = _parse_float(parts[-1])
        if value is not None:
            values.append(value)

    mean_value = statistics.mean(values) if values else 0.0
    median_value = statistics.median(values) if values else 0.0
    min_value = min(values) if values else 0.0
    max_value = max(values) if values else 0.0
    positive_count = sum(1 for value in values if value > 0)
    negative_count = sum(1 for value in values if value < 0)
    zero_count = sum(1 for value in values if value == 0)

    lines = [
        "Tajima's D summary",
        f"Input VCF: {Path(args.input_vcf)}",
        f"Window size: {args.window_size}",
        f"Tajima's D file: {result_path}",
        f"vcftools log: {log_path}",
        f"Total rows: {total_rows}",
        f"Rows with numeric Tajima's D: {len(values)}",
        f"Mean Tajima's D: {mean_value:.6f}",
        f"Median Tajima's D: {median_value:.6f}",
        f"Min Tajima's D: {min_value:.6f}",
        f"Max Tajima's D: {max_value:.6f}",
        f"Positive rows: {positive_count}",
        f"Negative rows: {negative_count}",
        f"Zero rows: {zero_count}",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
