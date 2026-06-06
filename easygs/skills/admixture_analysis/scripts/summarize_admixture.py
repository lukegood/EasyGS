#!/usr/bin/env python3
"""Summarize ADMIXTURE cross-validation outputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


CV_PATTERN = re.compile(r"CV error \(K=(\d+)\):\s*([0-9.eE+-]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize ADMIXTURE outputs.")
    parser.add_argument("--input-bfile", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dataset-prefix", required=True)
    parser.add_argument("--k-min", type=int, required=True)
    parser.add_argument("--k-max", type=int, required=True)
    parser.add_argument("--best-k-output", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _format_number(value: float) -> str:
    return f"{value:.6g}"


def _extract_cv_error(log_path: Path) -> float | None:
    if not log_path.exists():
        return None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = CV_PATTERN.search(line)
        if match:
            try:
                return float(match.group(2))
            except ValueError:
                return None
    return None


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    best_k_output = Path(args.best_k_output)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    best_k_output.parent.mkdir(parents=True, exist_ok=True)

    results: list[tuple[int, float]] = []
    for k in range(args.k_min, args.k_max + 1):
        value = _extract_cv_error(output_dir / f"log{k}.out")
        if value is not None:
            results.append((k, value))

    best_k: int | None = None
    best_cv: float | None = None
    if results:
        best_k, best_cv = min(results, key=lambda item: item[1])

    best_lines = []
    if best_k is not None and best_cv is not None:
        best_lines.append(f"K={best_k}")
        best_lines.append(f"CV_error={_format_number(best_cv)}")
    else:
        best_lines.append("K=n/a")
        best_lines.append("CV_error=n/a")
    best_k_output.write_text("\n".join(best_lines) + "\n", encoding="utf-8")

    lines = [
        "ADMIXTURE summary",
        f"Input BFILE: {Path(args.input_bfile)}",
        f"K range: {args.k_min}-{args.k_max}",
        f"Dataset prefix: {output_dir / args.dataset_prefix}",
        f"Best K: {best_k if best_k is not None else 'n/a'}",
        f"Best CV error: {_format_number(best_cv) if best_cv is not None else 'n/a'}",
        "CV errors by K:",
    ]
    if results:
        for k, value in results:
            lines.append(f"K={k}: {_format_number(value)}")
    else:
        lines.append("No valid CV error lines found in log files.")
    lines.extend(
        [
            "",
            f"Best K result file: {best_k_output}",
            "Generated admixture outputs:",
        ]
    )
    for k in range(args.k_min, args.k_max + 1):
        lines.append(f"- {output_dir / f'log{k}.out'}")
        lines.append(f"- {output_dir / f'{args.dataset_prefix}.{k}.Q'}")
        lines.append(f"- {output_dir / f'{args.dataset_prefix}.{k}.P'}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
