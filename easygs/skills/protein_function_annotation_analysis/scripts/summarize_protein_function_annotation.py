#!/usr/bin/env python3
"""Summarize protein function annotation outputs."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize protein function annotation outputs.")
    parser.add_argument("--genelist-txt", required=True, help="Input gene list TXT.")
    parser.add_argument("--longest-cds-txt", required=True, help="Maize longest-CDS mapping TXT.")
    parser.add_argument("--proteins-tsv", required=True, help="Maize protein annotation TSV.")
    parser.add_argument("--annotation-source", required=True, help="Selected annotation source or all.")
    parser.add_argument("--gene-protein-map-output", required=True, help="Generated gene-protein map TSV.")
    parser.add_argument("--protlist-output", required=True, help="Generated protlist.txt.")
    parser.add_argument("--protlist-stranno-output", required=True, help="Generated raw annotation TSV.")
    parser.add_argument("--annotation-tsv-output", required=True, help="Generated annotation TSV.")
    parser.add_argument("--summary-output", required=True, help="Summary output path.")
    return parser.parse_args()


def _count_nonempty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for line in handle if line.strip())


def _annotation_stats(path: Path) -> tuple[int, int, int, Counter[str], list[tuple[str, str, str, str]]]:
    if not path.exists():
        return 0, 0, 0, Counter(), []

    genes: set[str] = set()
    proteins: set[str] = set()
    sources: Counter[str] = Counter()
    examples: list[tuple[str, str, str, str]] = []
    row_count = 0

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            row_count += 1
            gene_id = (row.get("gene_id") or "").strip()
            protein_id = (row.get("protein_id") or "").strip()
            source = (row.get("analysis") or "").strip()
            signature = (row.get("signature_accession") or "").strip()
            description = (row.get("signature_description") or "").strip()

            if gene_id:
                genes.add(gene_id)
            if protein_id:
                proteins.add(protein_id)
            if source:
                sources[source] += 1
            if len(examples) < 5 and (signature or description):
                examples.append((gene_id, source, signature, description))

    return row_count, len(genes), len(proteins), sources, examples


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    gene_count = _count_nonempty_lines(Path(args.genelist_txt))
    gene_protein_pairs = _count_nonempty_lines(Path(args.gene_protein_map_output))
    protein_count = _count_nonempty_lines(Path(args.protlist_output))
    raw_annotation_rows = _count_nonempty_lines(Path(args.protlist_stranno_output))
    annotation_rows, annotated_genes, annotated_proteins, source_counts, examples = _annotation_stats(
        Path(args.annotation_tsv_output)
    )

    lines = [
        "=== 蛋白功能注释 ===",
        f"Gene list TXT: {args.genelist_txt}",
        f"Maize longest CDS resource: {args.longest_cds_txt}",
        f"Maize proteins TSV resource: {args.proteins_tsv}",
        f"Annotation source: {args.annotation_source or 'all'}",
        f"Gene-protein map TSV: {args.gene_protein_map_output}",
        f"protlist.txt: {args.protlist_output}",
        f"Raw protein annotation TSV: {args.protlist_stranno_output}",
        f"Protein function annotation TSV: {args.annotation_tsv_output}",
        f"Input genes: {gene_count}",
        f"Gene-protein pairs: {gene_protein_pairs}",
        f"Unique proteins: {protein_count}",
        f"Raw annotation rows: {raw_annotation_rows}",
        f"Annotation rows: {annotation_rows}",
        f"Annotated genes: {annotated_genes}",
        f"Annotated proteins: {annotated_proteins}",
    ]

    if source_counts:
        lines.append("Top annotation sources:")
        for source, count in source_counts.most_common(5):
            lines.append(f"- {source}: {count}")

    if examples:
        lines.append("Example annotations:")
        for gene_id, source, signature, description in examples:
            lines.append(f"- {gene_id}: {source} {signature} {description}".rstrip())

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
