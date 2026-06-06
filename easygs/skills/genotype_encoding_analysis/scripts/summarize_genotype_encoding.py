#!/usr/bin/env python3
"""Summarize PLINK additive genotype encoding output."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK --recodeA output.")
    parser.add_argument("--input-label", required=True, choices=["ped", "bfile"], help="Input type.")
    parser.add_argument("--input-path", required=True, help="Input PLINK prefix path.")
    parser.add_argument("--raw", required=True, help="PLINK .raw additive genotype matrix path.")
    parser.add_argument("--log", required=True, help="PLINK .log output path.")
    parser.add_argument("--nosex", required=True, help="PLINK .nosex output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_path = Path(args.raw)
    log_path = Path(args.log)
    nosex_path = Path(args.nosex)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sample_count = 0
    marker_count = 0
    missing_count = 0
    first_sample_id = ""
    header: list[str] = []

    with raw_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle):
            parts = line.rstrip("\n").split()
            if line_no == 0:
                header = parts
                marker_count = max(len(header) - 6, 0)
                continue
            if not parts:
                continue
            sample_count += 1
            if not first_sample_id and len(parts) >= 2:
                first_sample_id = f"{parts[0]}:{parts[1]}"
            for value in parts[6:]:
                if value.upper() in {"NA", "NAN", "."}:
                    missing_count += 1

    lines = [
        "=== PLINK genotype encoding summary ===",
        f"Input ({args.input_label}): {Path(args.input_path)}",
        f"Additive genotype matrix: {raw_path}",
        f"PLINK log: {log_path}",
        f"PLINK .nosex: {nosex_path if nosex_path.exists() else 'not generated'}",
        "",
        "Encoding:",
        "- 0: homozygous major allele",
        "- 1: heterozygous genotype",
        "- 2: homozygous minor allele",
        "",
        f"Sample count: {sample_count}",
        f"Encoded marker count: {marker_count}",
        f"Missing encoded values: {missing_count}",
    ]
    if first_sample_id:
        lines.append(f"First sample: {first_sample_id}")
    if header:
        preview_cols = header[: min(len(header), 12)]
        lines.append(f"Header preview: {' '.join(preview_cols)}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
