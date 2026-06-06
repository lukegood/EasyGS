#!/usr/bin/env python3
"""Summarize LD-pruning outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prune-in", required=True)
    parser.add_argument("--prune-out", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--input-label", required=True)
    parser.add_argument("--input-value", required=True)
    return parser.parse_args()


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for line in handle if line.strip())


def main() -> None:
    args = parse_args()
    prune_in = Path(args.prune_in)
    prune_out = Path(args.prune_out)
    output = Path(args.output)

    kept = count_lines(prune_in)
    removed = count_lines(prune_out)
    total = kept + removed
    kept_ratio = (kept / total) if total else 0.0

    lines = [
        "PLINK LD-prune summary",
        f"Input ({args.input_label}): {args.input_value}",
        f"Retained variants: {kept}",
        f"Pruned variants: {removed}",
        f"Total variants considered: {total}",
        f"Retained ratio: {kept_ratio:.6f}",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
