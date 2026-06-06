#!/usr/bin/env python3
"""Summarize PLINK MAF distribution output."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK MAF distribution output.")
    parser.add_argument("--input-bfile", required=True, help="Input PLINK BFILE prefix path.")
    parser.add_argument("--frq", required=True, help="PLINK .frq output path.")
    parser.add_argument("--log", required=True, help="PLINK .log output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_float(value: str) -> float | None:
    if value in {".", "NA", "NaN", "nan"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _format_percentage(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def main() -> None:
    args = parse_args()
    frq_path = Path(args.frq)
    log_path = Path(args.log)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [line.strip() for line in frq_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    data_rows = rows[1:] if rows else []

    labels = [
        "MAF<0.001",
        "0.001≤MAF<0.005",
        "0.005≤MAF<0.01",
        "0.01≤MAF<0.05",
        "MAF≥0.05",
    ]
    counts = {label: 0 for label in labels}
    invalid_rows = 0

    for line in data_rows:
        parts = line.split()
        if len(parts) < 5:
            invalid_rows += 1
            continue
        maf = _parse_float(parts[4])
        if maf is None:
            invalid_rows += 1
            continue
        if maf < 0.001:
            counts["MAF<0.001"] += 1
        elif maf < 0.005:
            counts["0.001≤MAF<0.005"] += 1
        elif maf < 0.01:
            counts["0.005≤MAF<0.01"] += 1
        elif maf < 0.05:
            counts["0.01≤MAF<0.05"] += 1
        else:
            counts["MAF≥0.05"] += 1

    total_sites = sum(counts.values())
    lines = [
        "=== PLINK MAF分布 ===",
        f"输入BFILE: {Path(args.input_bfile)}",
        f"频率文件: {frq_path}",
        f"PLINK日志: {log_path}",
        f"总位点数: {total_sites}",
    ]

    for label in labels:
        count = counts[label]
        percentage = (count / total_sites * 100.0) if total_sites else 0.0
        lines.append(f"{label}: {count} ({_format_percentage(percentage)}%)")

    if invalid_rows:
        lines.append(f"未解析位点数: {invalid_rows}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
