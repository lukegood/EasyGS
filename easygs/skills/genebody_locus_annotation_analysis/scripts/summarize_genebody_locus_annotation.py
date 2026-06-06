#!/usr/bin/env python3
"""Summarize genebody locus annotation outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize genebody locus annotation outputs.")
    parser.add_argument("--locus-list", required=True)
    parser.add_argument("--gene-bed", required=True)
    parser.add_argument("--site-gene-output", required=True)
    parser.add_argument("--gene-output", required=True)
    parser.add_argument("--summary-output", required=True)
    return parser.parse_args()


def _read_nonempty_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def main() -> int:
    args = parse_args()
    locus_path = Path(args.locus_list)
    site_gene_path = Path(args.site_gene_output)
    gene_path = Path(args.gene_output)
    summary_path = Path(args.summary_output)

    loci = _read_nonempty_lines(locus_path)
    site_gene_rows = _read_nonempty_lines(site_gene_path)
    genes = _read_nonempty_lines(gene_path)
    unique_loci = list(dict.fromkeys(row.split("\t", 1)[0] for row in site_gene_rows if row))
    unique_genes = list(dict.fromkeys(genes))

    lines = [
        "=== Genebody Locus Annotation ===",
        f"Locus list: {locus_path}",
        f"Built-in gene BED: {args.gene_bed}",
        f"Site-gene output: {site_gene_path}",
        f"Gene output: {gene_path}",
        f"Input loci: {len(loci)}",
        f"Genebody site-gene pairs: {len(site_gene_rows)}",
        f"Unique genebody loci: {len(unique_loci)}",
        f"Annotated genes: {len(genes)}",
        f"Unique annotated genes: {len(unique_genes)}",
    ]
    if site_gene_rows:
        lines.append("First site-gene pairs:")
        for row in site_gene_rows[:10]:
            lines.append(f"- {row}")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
