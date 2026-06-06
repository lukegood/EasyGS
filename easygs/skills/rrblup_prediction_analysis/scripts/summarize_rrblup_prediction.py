#!/usr/bin/env python3
"""Summarize rrBLUP genomic prediction outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize rrBLUP genomic prediction outputs.")
    parser.add_argument("--genotype-csvs", required=True)
    parser.add_argument("--phenotype-csvs", required=True)
    parser.add_argument("--cv-csvs", required=True)
    parser.add_argument("--trait-name", required=True)
    parser.add_argument("--id-column", required=True)
    parser.add_argument("--cv-column", required=True)
    parser.add_argument("--expected-folds", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--fold-metrics-output", required=True)
    parser.add_argument("--mean-effect-output", required=True)
    parser.add_argument("--mean-intercept-output", required=True)
    parser.add_argument("--summary-output", required=True)
    return parser.parse_args()


def _split_csv_arg(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def _read_fold_metrics(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    fold_metrics = _read_fold_metrics(Path(args.fold_metrics_output))
    train_values = [
        float(row["train_cor"])
        for row in fold_metrics
        if row.get("train_cor") not in (None, "", "NA")
    ]
    test_values = [
        float(row["test_cor"])
        for row in fold_metrics
        if row.get("test_cor") not in (None, "", "NA")
    ]

    lines = [
        "=== rrBLUP基因组预测 ===",
        f"Trait: {args.trait_name}",
        f"Genotype CSV count: {len(_split_csv_arg(args.genotype_csvs))}",
        f"Phenotype CSV count: {len(_split_csv_arg(args.phenotype_csvs))}",
        f"CV CSV count: {len(_split_csv_arg(args.cv_csvs))}",
        f"ID column: {args.id_column}",
        f"CV column: {args.cv_column}",
        f"Expected folds: {args.expected_folds}",
        f"Output dir: {args.output_dir}",
        f"Output prefix: {args.output_prefix}",
        f"Fold metrics rows: {len(fold_metrics)}",
        f"Mean train correlation: {sum(train_values) / len(train_values):.6f}" if train_values else "Mean train correlation: NA",
        f"Mean test correlation: {sum(test_values) / len(test_values):.6f}" if test_values else "Mean test correlation: NA",
        f"Mean effect rows: {_count_rows(Path(args.mean_effect_output))}",
        f"Mean intercept rows: {_count_rows(Path(args.mean_intercept_output))}",
    ]

    if fold_metrics:
        lines.append("Fold metrics preview:")
        for row in fold_metrics[:5]:
            lines.append(
                f"- fold={row.get('fold')}, train_n={row.get('train_n')}, "
                f"test_n={row.get('test_n')}, train_cor={row.get('train_cor')}, "
                f"test_cor={row.get('test_cor')}"
            )

    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
