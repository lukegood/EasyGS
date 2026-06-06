#!/usr/bin/env python3
"""Summarize PLINK PCA outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK PCA outputs.")
    parser.add_argument("--components", type=int, required=True)
    parser.add_argument("--input-bfile", required=True)
    parser.add_argument("--eigenval", required=True)
    parser.add_argument("--eigenvec", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _format_number(value: float) -> str:
    return f"{value:.6g}"


def main() -> None:
    args = parse_args()
    eigenval_path = Path(args.eigenval)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    eigenvalues: list[float] = []
    for line in eigenval_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            eigenvalues.append(float(stripped.split()[0]))
        except ValueError:
            continue

    total = sum(eigenvalues)
    lines = [
        "=== PCA统计 ===",
        f"主成分数: {args.components}",
        "总方差解释比例:",
        _format_number(total),
        "各主成分解释方差比例:",
    ]
    for index, value in enumerate(eigenvalues[: args.components], start=1):
        percentage = (value / total * 100.0) if total else 0.0
        lines.append(f"PC{index}: {_format_number(value)} ({_format_number(percentage)}%)")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
