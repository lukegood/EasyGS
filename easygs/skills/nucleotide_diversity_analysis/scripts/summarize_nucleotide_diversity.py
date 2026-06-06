#!/usr/bin/env python3
"""Summarize vcftools nucleotide-diversity output."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize vcftools nucleotide-diversity output.")
    parser.add_argument("--mode", required=True, choices=("site", "window"), help="Analysis mode.")
    parser.add_argument("--input-vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--result", required=True, help="vcftools output path (.sites.pi or .windowed.pi).")
    parser.add_argument("--log", required=True, help="vcftools .log output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    parser.add_argument("--window-size", type=int, help="Window size for window mode.")
    return parser.parse_args()


def _parse_float(token: str) -> float | None:
    if token in {".", "nan", "NaN", "inf", "-inf"}:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _format_float(value: float) -> str:
    return f"{value:.6f}"


def summarize_site(rows: list[str]) -> list[str]:
    total_sites = 0
    pi_values: list[float] = []

    for line in rows[1:] if rows else []:
        parts = line.split()
        if len(parts) < 3:
            continue
        total_sites += 1
        pi_value = _parse_float(parts[2])
        if pi_value is not None:
            pi_values.append(pi_value)

    mean_pi = statistics.mean(pi_values) if pi_values else 0.0
    median_pi = statistics.median(pi_values) if pi_values else 0.0
    min_pi = min(pi_values) if pi_values else 0.0
    max_pi = max(pi_values) if pi_values else 0.0

    return [
        f"Total site rows: {total_sites}",
        f"Sites with numeric PI: {len(pi_values)}",
        f"Mean site PI: {_format_float(mean_pi)}",
        f"Median site PI: {_format_float(median_pi)}",
        f"Min site PI: {_format_float(min_pi)}",
        f"Max site PI: {_format_float(max_pi)}",
    ]


def summarize_window(rows: list[str]) -> list[str]:
    total_windows = 0
    pi_values: list[float] = []
    variant_counts: list[int] = []

    for line in rows[1:] if rows else []:
        parts = line.split()
        if len(parts) < 5:
            continue
        total_windows += 1
        try:
            variant_counts.append(int(parts[3]))
        except ValueError:
            pass
        pi_value = _parse_float(parts[4])
        if pi_value is not None:
            pi_values.append(pi_value)

    mean_pi = statistics.mean(pi_values) if pi_values else 0.0
    median_pi = statistics.median(pi_values) if pi_values else 0.0
    min_pi = min(pi_values) if pi_values else 0.0
    max_pi = max(pi_values) if pi_values else 0.0
    mean_variants = statistics.mean(variant_counts) if variant_counts else 0.0

    return [
        f"Total windows: {total_windows}",
        f"Windows with numeric PI: {len(pi_values)}",
        f"Mean window PI: {_format_float(mean_pi)}",
        f"Median window PI: {_format_float(median_pi)}",
        f"Min window PI: {_format_float(min_pi)}",
        f"Max window PI: {_format_float(max_pi)}",
        f"Mean variant count per window: {_format_float(mean_variants)}",
    ]


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

    lines = [
        "Nucleotide diversity summary",
        f"Mode: {args.mode}",
        f"Input VCF: {Path(args.input_vcf)}",
        f"Result file: {result_path}",
        f"vcftools log: {log_path}",
    ]
    if args.window_size is not None:
        lines.append(f"Window size: {args.window_size}")

    if args.mode == "site":
        lines.extend(summarize_site(rows))
    else:
        lines.extend(summarize_window(rows))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
