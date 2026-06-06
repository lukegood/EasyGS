#!/usr/bin/env python3
"""Summarize Fast3VmrMLM QEI detection outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Fast3VmrMLM QEI outputs.")
    parser.add_argument("--bfile-prefix", required=True, help="Input BFILE prefix.")
    parser.add_argument("--phenotype-csv", required=True, help="Input phenotype CSV.")
    parser.add_argument("--structure-csv", required=True, help="Input structure CSV.")
    parser.add_argument("--output-prefix", required=True, help="Output file prefix.")
    parser.add_argument("--summary-output", required=True, help="Summary output path.")
    parser.add_argument("--trait-count", required=True, type=int, help="Trait count.")
    parser.add_argument("--n-en", required=True, help="Comma-separated n_en vector.")
    parser.add_argument("--draw-plot", required=True, help="Whether plots were requested.")
    return parser.parse_args()


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def _shape_csv(path: Path) -> tuple[int, int]:
    if not path.exists():
        return (0, 0)
    rows = 0
    max_cols = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            rows += 1
            max_cols = max(max_cols, len(row))
    return rows, max_cols


def _parse_bool(value: str) -> bool:
    return value.strip().upper() in {"TRUE", "T", "1", "YES", "Y"}


def main() -> None:
    args = parse_args()
    output_prefix = Path(args.output_prefix)
    output_dir = output_prefix.parent
    prefix_text = str(output_prefix)
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    prekinship_path = Path(f"{prefix_text}preKinship.csv")
    midresult_paths = [
        Path(f"{prefix_text}trait_{index}_midresult.csv")
        for index in range(1, args.trait_count + 1)
    ]
    result_xlsx_paths = [
        Path(f"{prefix_text}trait_{index}_result.xlsx")
        for index in range(1, args.trait_count + 1)
    ]
    plot_requested = _parse_bool(args.draw_plot)
    plot_files = sorted(path.name for path in output_dir.glob(f"{output_prefix.name}*.tif*"))

    lines = [
        "=== QEI 检测 ===",
        f"BFILE prefix: {args.bfile_prefix}",
        f"Phenotype CSV: {args.phenotype_csv}",
        f"Structure CSV: {args.structure_csv}",
        f"Output prefix: {output_prefix}",
        f"Trait count: {args.trait_count}",
        f"n_en: {args.n_en}",
        f"Pre-kinship CSV exists: {'yes' if prekinship_path.exists() else 'no'}",
    ]

    if prekinship_path.exists():
        rows, cols = _shape_csv(prekinship_path)
        lines.append(f"Pre-kinship CSV shape: {rows} rows x {cols} columns")

    for index, path in enumerate(midresult_paths, start=1):
        lines.append(f"trait_{index} midresult exists: {'yes' if path.exists() else 'no'}")
        if path.exists():
            lines.append(f"trait_{index} midresult rows: {_count_csv_rows(path)}")

    for index, path in enumerate(result_xlsx_paths, start=1):
        lines.append(f"trait_{index} result xlsx exists: {'yes' if path.exists() else 'no'}")

    lines.append(f"Plot requested: {'yes' if plot_requested else 'no'}")
    lines.append(f"TIFF plot count: {len(plot_files)}")
    for name in plot_files[:10]:
        lines.append(f"TIFF plot: {name}")

    generated = sorted(
        path.name for path in output_dir.iterdir() if path.is_file() and path.name.startswith(output_prefix.name)
    ) if output_dir.exists() else []
    lines.append(f"Generated output files: {len(generated)}")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
