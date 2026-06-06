#!/usr/bin/env python3
"""汇总 CVF 划分结果。"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Summarize CVF split outputs.")
    parser.add_argument("--list-txt", required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sample-column", required=True)
    parser.add_argument("--cv-column", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-output", required=True)
    return parser.parse_args()


def read_output_rows(path: Path) -> list[dict[str, str]]:
    """读取输出 CSV。"""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    """生成摘要文本。"""
    args = parse_args()
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    rows = read_output_rows(output_path)
    fold_counts = Counter()
    for row in rows:
        fold_value = row.get(args.cv_column, "").strip()
        if fold_value:
            fold_counts[fold_value] += 1

    lines = [
        "=== CVF Split Summary ===",
        f"Input LIST: {args.list_txt}",
        f"Sample column: {args.sample_column}",
        f"CV column: {args.cv_column}",
        f"Fold count: {args.k}",
        f"Random seed: {args.seed}",
        f"Output CSV: {args.output_csv}",
        f"Sample count: {len(rows)}",
    ]

    if fold_counts:
        lines.append("Fold distribution:")
        for fold in sorted(fold_counts, key=lambda value: int(value)):
            lines.append(f"- fold {fold}: {fold_counts[fold]}")

    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
