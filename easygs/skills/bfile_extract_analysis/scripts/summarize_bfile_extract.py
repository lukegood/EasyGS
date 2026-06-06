#!/usr/bin/env python3
"""Summarize extracted BFILE outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize BFILE extraction outputs.")
    parser.add_argument("--input-bfile", required=True)
    parser.add_argument("--extract-file", required=True)
    parser.add_argument("--out-prefix", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _count_non_empty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def main() -> None:
    args = parse_args()
    out_prefix = Path(args.out_prefix)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    requested = _count_non_empty_lines(Path(args.extract_file))
    retained = _count_non_empty_lines(out_prefix.with_suffix(".bim"))
    samples = _count_non_empty_lines(out_prefix.with_suffix(".fam"))

    lines = [
        "BFILE extract summary",
        f"Input BFILE: {Path(args.input_bfile)}",
        f"Extract file: {Path(args.extract_file)}",
        f"Requested variants: {requested}",
        f"Retained variants: {retained}",
        f"Samples retained: {samples}",
        f"Generated BED file: {out_prefix}.bed",
        f"Generated BIM file: {out_prefix}.bim",
        f"Generated FAM file: {out_prefix}.fam",
    ]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
