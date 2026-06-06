#!/usr/bin/env python3
"""Summarize PLINK regional R2 output."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK regional R2 output.")
    parser.add_argument("--input-bfile", required=True, help="Input PLINK BFILE prefix path.")
    parser.add_argument("--chromosome", required=True, help="Chromosome passed to PLINK --chr.")
    parser.add_argument("--from-bp", type=int, required=True, help="Region start passed to PLINK --from-bp.")
    parser.add_argument("--to-bp", type=int, required=True, help="Region end passed to PLINK --to-bp.")
    parser.add_argument("--ld-window", type=int, required=True, help="PLINK --ld-window value.")
    parser.add_argument("--ld-window-kb", type=int, help="Optional PLINK --ld-window-kb value.")
    parser.add_argument("--ld-window-r2", type=float, required=True, help="PLINK --ld-window-r2 value.")
    parser.add_argument("--ld", required=True, help="PLINK .ld output path.")
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
    ld_path = Path(args.ld)
    log_path = Path(args.log)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [line.strip() for line in ld_path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    if not rows:
        header: list[str] = []
        data_rows: list[str] = []
    else:
        header = rows[0].split()
        data_rows = rows[1:]

    column_index = {name: index for index, name in enumerate(header)}
    r2_values: list[float] = []
    pair_distances: list[int] = []
    variants: set[str] = set()

    for line in data_rows:
        parts = line.split()
        r2_idx = column_index.get("R2")
        if r2_idx is None or r2_idx >= len(parts):
            continue
        r2 = _parse_float(parts[r2_idx])
        if r2 is None:
            continue
        r2_values.append(r2)

        for snp_key in ("SNP_A", "SNP_B"):
            idx = column_index.get(snp_key)
            if idx is not None and idx < len(parts):
                variants.add(parts[idx])

        bp_a_idx = column_index.get("BP_A")
        bp_b_idx = column_index.get("BP_B")
        if bp_a_idx is not None and bp_b_idx is not None and bp_a_idx < len(parts) and bp_b_idx < len(parts):
            bp_a = _parse_int(parts[bp_a_idx])
            bp_b = _parse_int(parts[bp_b_idx])
            if bp_a is not None and bp_b is not None:
                pair_distances.append(abs(bp_b - bp_a))

    pair_count = len(r2_values)
    mean_r2 = statistics.mean(r2_values) if r2_values else 0.0
    max_r2 = max(r2_values) if r2_values else 0.0
    mean_distance = statistics.mean(pair_distances) if pair_distances else 0.0
    high_ld_pairs = sum(1 for value in r2_values if value >= 0.2)
    very_high_ld_pairs = sum(1 for value in r2_values if value >= 0.8)

    lines = [
        "=== 特定区域R²统计 ===",
        f"输入BFILE: {Path(args.input_bfile)}",
        f"区域: chr{args.chromosome}:{args.from_bp}-{args.to_bp}",
        f"LD文件: {ld_path}",
        f"PLINK日志: {log_path}",
        f"位点窗口数限制 (--ld-window): {args.ld_window}",
        f"R²输出阈值 (--ld-window-r2): {args.ld_window_r2:.6f}",
        f"R²位点对数量: {pair_count}",
        f"参与位点数: {len(variants)}",
        f"平均R²: {mean_r2:.6f}",
        f"最大R²: {max_r2:.6f}",
        f"R²≥0.2 的位点对数量: {high_ld_pairs}",
        f"R²≥0.8 的位点对数量: {very_high_ld_pairs}",
    ]
    if args.ld_window_kb is not None:
        lines.insert(7, f"距离窗口限制 (--ld-window-kb): {args.ld_window_kb}")
    if pair_distances:
        lines.append(f"平均位点间距离(bp): {mean_distance:.2f}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
