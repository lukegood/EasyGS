#!/usr/bin/env python3
"""Summarize cross-region phenotype correlation outputs."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize cross-region phenotype correlation outputs.")
    parser.add_argument("--input-csv", required=True, help="Original phe.csv input path.")
    parser.add_argument("--correlation-csv", required=True, help="Generated correlation CSV path.")
    parser.add_argument("--heatmap-pdf", required=True, help="Generated heatmap PDF path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _inspect_input(path: Path) -> tuple[int, int, list[str]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return 0, 0, []
        id_key = "ID" if "ID" in fieldnames else fieldnames[0]
        phenotype_labels = [name for name in fieldnames if name != id_key]
        sample_count = sum(1 for _ in reader)
        return sample_count, len(phenotype_labels), phenotype_labels


def _load_correlation_matrix(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.reader(handle))

    if not rows or len(rows[0]) < 2:
        raise ValueError(f"Correlation CSV is empty or malformed: {path}")

    labels = [item.strip() for item in rows[0][1:] if item.strip()]
    matrix: list[list[float]] = []
    for row in rows[1:]:
        if len(row) < len(labels) + 1:
            continue
        values: list[float] = []
        for raw_value in row[1 : len(labels) + 1]:
            try:
                values.append(float(raw_value))
            except ValueError:
                values.append(math.nan)
        matrix.append(values)

    if not labels or not matrix:
        raise ValueError(f"Correlation CSV does not contain usable phenotype data: {path}")
    return labels, matrix


def _pair_summaries(labels: list[str], matrix: list[list[float]]) -> tuple[str, str, float, list[str]]:
    strongest_positive: tuple[str, float] | None = None
    strongest_negative: tuple[str, float] | None = None
    absolute_pairs: list[tuple[float, str]] = []
    abs_values: list[float] = []

    for i in range(min(len(labels), len(matrix))):
        row = matrix[i]
        for j in range(i + 1, min(len(labels), len(row))):
            value = row[j]
            if math.isnan(value):
                continue
            label = f"{labels[i]} vs {labels[j]}: {value:.6f}"
            absolute_pairs.append((abs(value), label))
            abs_values.append(abs(value))
            if strongest_positive is None or value > strongest_positive[1]:
                strongest_positive = (label, value)
            if strongest_negative is None or value < strongest_negative[1]:
                strongest_negative = (label, value)

    strongest_positive_label = strongest_positive[0] if strongest_positive else "n/a"
    strongest_negative_label = strongest_negative[0] if strongest_negative else "n/a"
    mean_abs = sum(abs_values) / len(abs_values) if abs_values else 0.0
    top_pairs = [label for _, label in sorted(absolute_pairs, key=lambda item: item[0], reverse=True)[:5]]
    return strongest_positive_label, strongest_negative_label, mean_abs, top_pairs


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    correlation_csv = Path(args.correlation_csv)
    heatmap_pdf = Path(args.heatmap_pdf)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sample_count, phenotype_count, phenotype_labels = _inspect_input(input_csv)
    labels, matrix = _load_correlation_matrix(correlation_csv)
    strongest_positive, strongest_negative, mean_abs, top_pairs = _pair_summaries(labels, matrix)

    lines = [
        "=== 各地区表型相关性分析 ===",
        f"输入CSV: {input_csv}",
        f"样本数量: {sample_count}",
        f"表型列数量: {phenotype_count}",
        f"相关矩阵文件: {correlation_csv}",
        f"热图PDF: {heatmap_pdf}",
        f"平均绝对相关系数: {mean_abs:.6f}",
        f"最强正相关: {strongest_positive}",
        f"最强负相关: {strongest_negative}",
    ]
    if phenotype_labels:
        lines.append(f"表型列: {', '.join(phenotype_labels)}")
    if top_pairs:
        lines.append("绝对值最高的前5对相关性:")
        lines.extend(top_pairs)

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
