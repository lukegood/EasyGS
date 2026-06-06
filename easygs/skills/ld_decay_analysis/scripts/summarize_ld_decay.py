#!/usr/bin/env python3
"""Summarize PopLDdecay output."""

from __future__ import annotations

import argparse
import gzip
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PopLDdecay output.")
    parser.add_argument("--input-vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--stat", required=True, help="PopLDdecay .stat.gz output path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_float(value: str) -> float | None:
    if value in {".", "NA", "NaN", "nan"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _is_header(tokens: list[str]) -> bool:
    return any(any(char.isalpha() for char in token) for token in tokens)


def _pick_index(header: list[str], candidates: tuple[str, ...]) -> int | None:
    lowered = [item.lower() for item in header]
    for candidate in candidates:
        for index, item in enumerate(lowered):
            if candidate in item:
                return index
    return None


def main() -> None:
    args = parse_args()
    stat_path = Path(args.stat)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with gzip.open(stat_path, "rt", encoding="utf-8", errors="replace") as handle:
        rows = [line.strip() for line in handle if line.strip()]

    if rows:
        first_tokens = rows[0].split()
        has_header = _is_header(first_tokens)
    else:
        first_tokens = []
        has_header = False

    header = first_tokens if has_header else []
    data_rows = rows[1:] if has_header else rows

    distance_values: list[float] = []
    r2_values: list[float] = []

    distance_index = _pick_index(header, ("dist", "distance", "kb")) if header else None
    r2_index = _pick_index(header, ("r2", "r^2", "rr")) if header else None

    for line in data_rows:
        parts = line.split()
        if not parts:
            continue

        numeric_values = [(_parse_float(token), index) for index, token in enumerate(parts)]
        numeric_values = [(value, index) for value, index in numeric_values if value is not None]
        if not numeric_values:
            continue

        dist_value = None
        if distance_index is not None and distance_index < len(parts):
            dist_value = _parse_float(parts[distance_index])
        elif numeric_values:
            dist_value = numeric_values[0][0]

        r2_value = None
        if r2_index is not None and r2_index < len(parts):
            r2_value = _parse_float(parts[r2_index])
        else:
            for value, index in numeric_values:
                if distance_index is not None and index == distance_index:
                    continue
                r2_value = value
                break

        if dist_value is not None:
            distance_values.append(dist_value)
        if r2_value is not None:
            r2_values.append(r2_value)

    point_count = len(data_rows)
    mean_r2 = statistics.mean(r2_values) if r2_values else 0.0
    max_r2 = max(r2_values) if r2_values else 0.0

    below_half_distance = None
    below_point_two_distance = None
    if distance_values and r2_values:
        for distance, r2 in zip(distance_values, r2_values, strict=False):
            if below_half_distance is None and r2 <= 0.5:
                below_half_distance = distance
            if below_point_two_distance is None and r2 <= 0.2:
                below_point_two_distance = distance

    lines = [
        "=== PopLDdecay LD衰减统计 ===",
        f"输入VCF: {Path(args.input_vcf)}",
        f"统计文件: {stat_path}",
        f"统计点数: {point_count}",
    ]
    if distance_values:
        lines.append(f"距离范围: {min(distance_values):.6f} - {max(distance_values):.6f}")
    if r2_values:
        lines.extend(
            [
                f"平均LD值: {mean_r2:.6f}",
                f"最大LD值: {max_r2:.6f}",
            ]
        )
    if below_half_distance is not None:
        lines.append(f"LD≤0.5时的最早距离: {below_half_distance:.6f}")
    if below_point_two_distance is not None:
        lines.append(f"LD≤0.2时的最早距离: {below_point_two_distance:.6f}")
    if header:
        lines.append(f"解析表头: {' '.join(header)}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
