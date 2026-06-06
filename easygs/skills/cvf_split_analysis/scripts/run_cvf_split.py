#!/usr/bin/env python3
"""生成 CVF 划分结果。"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

ALLOWED_SAMPLE_HEADERS = (
    "id",
    "list_id",
    "sample_id",
    "line_id",
    "material_id",
    "sampleid",
    "lineid",
    "materialid",
    "listid",
)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Generate a CVF CSV from a material LIST TXT.")
    parser.add_argument("--list-txt", required=True)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sample-column", required=True)
    parser.add_argument("--cv-column", required=True)
    parser.add_argument("--output-csv", required=True)
    return parser.parse_args()


def read_list_file(path: Path) -> tuple[str, list[str]]:
    """读取并校验 LIST 文件。"""
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    rows = [line for line in lines if line]
    if not rows:
        raise ValueError(f"LIST TXT is empty: {path}")

    sample_column = rows[0]
    sample_ids = rows[1:]
    if not sample_column:
        raise ValueError(f"LIST TXT header is empty: {path}")
    if sample_column.lower() not in ALLOWED_SAMPLE_HEADERS:
        allowed_headers = ", ".join(ALLOWED_SAMPLE_HEADERS)
        raise ValueError(
            "LIST TXT header must be one of the supported sample column names. "
            f"header={sample_column}, allowed={allowed_headers}"
        )
    if not sample_ids:
        raise ValueError(f"LIST TXT must contain a header and at least one material ID: {path}")

    duplicates: list[str] = []
    seen: set[str] = set()
    for sample_id in sample_ids:
        if not sample_id:
            raise ValueError(f"LIST TXT contains an empty material ID: {path}")
        if sample_id in seen and sample_id not in duplicates:
            duplicates.append(sample_id)
        seen.add(sample_id)
    if duplicates:
        duplicate_text = ", ".join(duplicates[:10])
        raise ValueError(f"LIST TXT contains duplicate material IDs: {duplicate_text}")

    return sample_column, sample_ids


def assign_folds(sample_ids: list[str], folds: int, seed: int) -> dict[str, int]:
    """按轮转方式为样本分配折号。"""
    if folds < 2:
        raise ValueError("k must be at least 2.")
    if len(sample_ids) < folds:
        raise ValueError(
            f"Sample count must be greater than or equal to k. samples={len(sample_ids)}, k={folds}"
        )

    shuffled = list(sample_ids)
    random.Random(seed).shuffle(shuffled)

    assignments: dict[str, int] = {}
    for index, sample_id in enumerate(shuffled):
        assignments[sample_id] = (index % folds) + 1
    return assignments


def write_output(path: Path, sample_column: str, cv_column: str, sample_ids: list[str], assignments: dict[str, int]) -> None:
    """按原始输入顺序写出结果。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([sample_column, cv_column])
        for sample_id in sample_ids:
            writer.writerow([sample_id, assignments[sample_id]])


def main() -> int:
    """执行主流程。"""
    args = parse_args()
    list_path = Path(args.list_txt)
    sample_column, sample_ids = read_list_file(list_path)
    if sample_column != args.sample_column:
        raise ValueError(
            f"Sample column does not match the prepared value. expected={args.sample_column}, actual={sample_column}"
        )

    assignments = assign_folds(sample_ids, args.k, args.seed)
    write_output(
        path=Path(args.output_csv),
        sample_column=args.sample_column,
        cv_column=args.cv_column,
        sample_ids=sample_ids,
        assignments=assignments,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
