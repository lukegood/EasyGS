#!/usr/bin/env python3
"""Summarize GRM outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize GCTA GRM outputs.")
    parser.add_argument("--input-bfile", required=True)
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
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    id_path = out_prefix.with_suffix(".grm.id")
    lines = [
        "GRM summary",
        f"Input BFILE: {Path(args.input_bfile)}",
        f"Sample count in GRM: {_count_non_empty_lines(id_path)}",
        f"GRM bin: {out_prefix}.grm.bin",
        f"GRM id: {id_path}",
        f"GRM N bin: {out_prefix}.grm.N.bin",
        f"GCTA log: {out_prefix}.log",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
