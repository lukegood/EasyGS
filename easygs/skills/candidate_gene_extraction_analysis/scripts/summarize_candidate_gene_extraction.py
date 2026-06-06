#!/usr/bin/env python3
"""Summarize candidate gene extraction outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize candidate gene extraction outputs.")
    parser.add_argument("--bed", required=True)
    parser.add_argument("--ld-distance", required=True, type=int)
    parser.add_argument("--gene-bed", required=True)
    parser.add_argument("--extended-bed-output", required=True)
    parser.add_argument("--gene-list-output", required=True)
    parser.add_argument("--summary-output", required=True)
    return parser.parse_args()


def _read_nonempty_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]


def main() -> int:
    args = parse_args()
    bed_path = Path(args.bed)
    extended_bed_path = Path(args.extended_bed_output)
    gene_list_path = Path(args.gene_list_output)
    summary_path = Path(args.summary_output)

    bed_rows = _read_nonempty_lines(bed_path)
    extended_rows = _read_nonempty_lines(extended_bed_path)
    genes = _read_nonempty_lines(gene_list_path)
    unique_genes = list(dict.fromkeys(genes))

    lines = [
        "=== 候选基因提取 ===",
        f"BED: {bed_path}",
        f"LD distance: {args.ld_distance}bp",
        f"Gene annotation BED: {args.gene_bed}",
        f"Extended BED: {extended_bed_path}",
        f"Gene list: {gene_list_path}",
        f"Input BED rows: {len(bed_rows)}",
        f"Extended BED rows: {len(extended_rows)}",
        f"Candidate genes: {len(genes)}",
        f"Unique candidate genes: {len(unique_genes)}",
    ]
    if unique_genes:
        lines.append("First candidate genes:")
        for gene in unique_genes[:10]:
            lines.append(f"- {gene}")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
