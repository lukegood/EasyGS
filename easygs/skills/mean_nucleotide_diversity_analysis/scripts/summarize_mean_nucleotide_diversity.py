#!/usr/bin/env python3
"""Summarize mean nucleotide diversity from a vcftools .sites.pi file."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize mean nucleotide diversity from a .sites.pi file.")
    parser.add_argument("--sites-pi", required=True, help="Input vcftools .sites.pi file.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _parse_float(token: str) -> float | None:
    if token in {".", "nan", "NaN", "inf", "-inf"}:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    sites_pi_path = Path(args.sites_pi)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    values: list[float] = []
    rows = [
        line.strip()
        for line in sites_pi_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    for line in rows[1:] if rows else []:
        parts = line.split()
        if len(parts) < 3:
            continue
        value = _parse_float(parts[2])
        if value is not None:
            values.append(value)

    mean_pi = statistics.mean(values) if values else 0.0
    lines = [
        "=== 核苷酸多样性(π) ===",
        f"平均π: {mean_pi:.6f}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
