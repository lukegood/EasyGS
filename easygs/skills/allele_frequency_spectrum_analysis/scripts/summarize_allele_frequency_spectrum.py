#!/usr/bin/env python3
"""Summarize PLINK allele-frequency spectrum output."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK allele-frequency spectrum output.")
    parser.add_argument("--input-bfile", required=True, help="Input PLINK BFILE prefix path.")
    parser.add_argument("--frqx", required=True, help="PLINK .frqx output path.")
    parser.add_argument("--log", required=True, help="PLINK .log output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_int(value: str) -> int | None:
    if value in {".", "NA", "NaN", "nan"}:
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
    frqx_path = Path(args.frqx)
    log_path = Path(args.log)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [line.strip() for line in frqx_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    data_rows = rows[1:] if rows else []

    total_sites = 0
    polymorphic_sites = 0
    singleton_sites = 0
    doubleton_sites = 0
    minor_allele_counts: list[int] = []
    missing_counts: list[int] = []

    for line in data_rows:
        parts = line.split()
        if len(parts) < 10:
            continue

        hom_a1 = _parse_int(parts[4])
        het = _parse_int(parts[5])
        hom_a2 = _parse_int(parts[6])
        hap_a1 = _parse_int(parts[7])
        hap_a2 = _parse_int(parts[8])
        missing = _parse_int(parts[9])
        if None in {hom_a1, het, hom_a2, hap_a1, hap_a2, missing}:
            continue

        total_sites += 1
        allele_a1 = 2 * hom_a1 + het + hap_a1
        allele_a2 = 2 * hom_a2 + het + hap_a2
        minor_count = min(allele_a1, allele_a2)
        missing_counts.append(missing)

        if allele_a1 > 0 and allele_a2 > 0:
            polymorphic_sites += 1
            minor_allele_counts.append(minor_count)
            if minor_count == 1:
                singleton_sites += 1
            elif minor_count == 2:
                doubleton_sites += 1

    proportion = (polymorphic_sites / total_sites) if total_sites else 0.0
    mean_minor_count = statistics.mean(minor_allele_counts) if minor_allele_counts else 0.0
    mean_missing = statistics.mean(missing_counts) if missing_counts else 0.0

    lines = [
        "=== PLINK 等位基因频率谱 ===",
        f"输入BFILE: {Path(args.input_bfile)}",
        f"频率谱文件: {frqx_path}",
        f"PLINK日志: {log_path}",
        f"总位点数: {total_sites}",
        f"多态位点数: {polymorphic_sites}",
        f"多态位点比例: {proportion:.6f}",
        f"Singleton位点数 (MAC=1): {singleton_sites}",
        f"Doubleton位点数 (MAC=2): {doubleton_sites}",
        f"平均次要等位基因计数 (多态位点): {mean_minor_count:.6f}",
        f"平均缺失基因型计数: {mean_missing:.6f}",
    ]

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
