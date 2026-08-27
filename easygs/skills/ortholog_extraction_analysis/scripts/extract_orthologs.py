#!/usr/bin/env python3
"""Extract ortholog matrix rows by exact source-gene ID matching."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract exact source-gene ortholog rows.")
    parser.add_argument("--genelist-txt", required=True)
    parser.add_argument("--ortholog-matrix-tsv", required=True)
    parser.add_argument("--output-tsv", required=True)
    return parser.parse_args()


def _read_requested_genes(path: Path) -> set[str]:
    genes: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            gene = raw.strip().lstrip("\ufeff")
            if gene:
                genes.add(gene)
    return genes


def main() -> int:
    args = parse_args()
    genelist_path = Path(args.genelist_txt)
    matrix_path = Path(args.ortholog_matrix_tsv)
    output_path = Path(args.output_tsv)
    requested_genes = _read_requested_genes(genelist_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    matched_rows = 0
    with (
        matrix_path.open("r", encoding="utf-8", errors="replace", newline="") as matrix,
        output_path.open("w", encoding="utf-8", newline="") as output,
    ):
        for raw in matrix:
            source_gene = raw.split("\t", 1)[0].strip().lstrip("\ufeff")
            if source_gene not in requested_genes:
                continue
            output.write(raw)
            if raw and not raw.endswith(("\n", "\r")):
                output.write("\n")
            matched_rows += 1

    print(f"Extracted {matched_rows} ortholog rows to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
