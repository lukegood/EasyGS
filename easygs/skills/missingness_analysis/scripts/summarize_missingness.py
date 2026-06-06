#!/usr/bin/env python3
"""Summarize PLINK missingness outputs."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--imiss", required=True)
    parser.add_argument("--lmiss", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-threshold", type=float, required=True)
    parser.add_argument("--variant-threshold", type=float, required=True)
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split()
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        values = line.split()
        row = {key: value for key, value in zip(header, values, strict=False)}
        if row:
            rows.append(row)
    return rows


def summarize_distribution(values: list[float]) -> str:
    if not values:
        return "n/a"
    return (
        f"min={min(values):.6f}, mean={statistics.mean(values):.6f}, "
        f"median={statistics.median(values):.6f}, max={max(values):.6f}"
    )


def format_top(rows: list[dict[str, str]], label_keys: list[str], threshold: float, max_items: int = 10) -> list[str]:
    flagged = [row for row in rows if float(row["F_MISS"]) > threshold]
    flagged.sort(key=lambda row: float(row["F_MISS"]), reverse=True)
    if not flagged:
        return ["none"]
    lines: list[str] = []
    for row in flagged[:max_items]:
        label = "/".join(str(row[key]) for key in label_keys)
        lines.append(f"{label}: {float(row['F_MISS']):.6f}")
    return lines


def main() -> None:
    args = parse_args()
    imiss_path = Path(args.imiss)
    lmiss_path = Path(args.lmiss)
    output_path = Path(args.output)

    sample_rows = read_rows(imiss_path)
    variant_rows = read_rows(lmiss_path)

    sample_values = [float(row["F_MISS"]) for row in sample_rows]
    variant_values = [float(row["F_MISS"]) for row in variant_rows]

    lines = [
        "PLINK missingness summary",
        f"Sample count: {len(sample_rows)}",
        f"Variant count: {len(variant_rows)}",
        f"Sample missingness distribution: {summarize_distribution(sample_values)}",
        f"Variant missingness distribution: {summarize_distribution(variant_values)}",
        f"High-missingness sample threshold: > {args.sample_threshold:.6f}",
        "High-missingness samples:",
    ]
    lines.extend(format_top(sample_rows, ["FID", "IID"], args.sample_threshold))
    lines.extend(
        [
            "",
            f"High-missingness variant threshold: > {args.variant_threshold:.6f}",
            "High-missingness variants:",
        ]
    )
    lines.extend(format_top(variant_rows, ["CHR", "SNP"], args.variant_threshold))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
