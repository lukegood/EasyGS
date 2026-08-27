#!/usr/bin/env python3
"""Summarize wheat/rice offline GO and KEGG enrichment outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--species", required=True)
    parser.add_argument("--analysis-type", required=True)
    parser.add_argument("--genelist-txt", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--gene2ko-tsv")
    parser.add_argument("--kegg-annotation-tsv")
    parser.add_argument("--kegg-all-output")
    parser.add_argument("--kegg-significant-output")
    parser.add_argument("--kegg-mapped-output")
    parser.add_argument("--kegg-plot-output")
    parser.add_argument("--gene2go-tsv")
    parser.add_argument("--go-term-tsv")
    parser.add_argument("--go-all-output")
    parser.add_argument("--go-significant-output")
    parser.add_argument("--go-mapped-output")
    parser.add_argument("--go-plot-output")
    return parser.parse_args()


def count_nonempty_lines(path_value: str | None) -> int:
    if not path_value:
        return 0
    path = Path(path_value)
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def count_table_rows(path_value: str | None) -> int:
    count = count_nonempty_lines(path_value)
    return max(0, count - 1)


def read_gene_ids(path_value: str) -> set[str]:
    path = Path(path_value)
    return {
        line.split("\t", 1)[0].strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    }


def count_term_mapped_genes(
    genelist_path: str,
    mapping_path: str | None,
    annotation_path: str | None,
    *,
    mapping_term_column: str,
    annotation_term_column: str,
) -> int:
    if not mapping_path or not annotation_path:
        return 0
    input_genes = read_gene_ids(genelist_path)
    annotation_terms: set[str] = set()
    with Path(annotation_path).open(
        "r", encoding="utf-8-sig", errors="replace", newline=""
    ) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            value = (row.get(annotation_term_column) or "").strip()
            if value:
                annotation_terms.add(value)

    mapped_genes: set[str] = set()
    with Path(mapping_path).open(
        "r", encoding="utf-8-sig", errors="replace", newline=""
    ) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            gene = (row.get("locusName") or "").strip()
            term = (row.get(mapping_term_column) or "").strip()
            if gene in input_genes and term in annotation_terms:
                mapped_genes.add(gene)
    return len(mapped_genes)


def top_terms(path_value: str | None, limit: int = 5) -> list[str]:
    if not path_value:
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    terms: list[str] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            identifier = (row.get("ID") or "").strip()
            description = (row.get("Description") or "").strip()
            pvalue = (row.get("pvalue") or "").strip()
            if identifier or description:
                terms.append(f"{identifier}\t{description}\tp={pvalue}")
            if len(terms) >= limit:
                break
    return terms


def append_branch(
    lines: list[str],
    *,
    title: str,
    mapping_resource: str | None,
    annotation_resource: str | None,
    mapped_output: str | None,
    all_output: str | None,
    significant_output: str | None,
    plot_output: str | None,
    term_mapped_label: str,
    term_mapped_count: int,
) -> None:
    lines.extend(
        [
            "",
            f"{title}:",
            f"Mapping resource: {mapping_resource}",
            f"Annotation resource: {annotation_resource}",
            f"Mapped genes: {count_nonempty_lines(mapped_output)}",
            f"{term_mapped_label}: {term_mapped_count}",
            f"All enriched terms: {count_table_rows(all_output)}",
            f"Significant terms (p < 0.1 and q < 0.2): {count_table_rows(significant_output)}",
            f"All-result table: {all_output}",
            f"Significant-result table: {significant_output}",
            f"Mapped-gene file: {mapped_output}",
            f"Plot: {plot_output}",
            f"Plot exists: {'yes' if plot_output and Path(plot_output).exists() else 'no'}",
        ]
    )
    terms = top_terms(all_output)
    if terms:
        lines.append("Top terms:")
        lines.extend(f"- {term}" for term in terms)


def main() -> None:
    args = parse_args()
    lines = [
        "Wheat/Rice Gene Function Enrichment Summary",
        f"Species: {args.species}",
        f"Analysis type: {args.analysis_type}",
        f"Gene list: {args.genelist_txt}",
        f"Input genes: {count_nonempty_lines(args.genelist_txt)}",
        "Significance rule: p < 0.1 and q < 0.2",
    ]
    if args.analysis_type in {"ALL", "KEGG"}:
        kegg_pathway_mapped = count_term_mapped_genes(
            args.genelist_txt,
            args.gene2ko_tsv,
            args.kegg_annotation_tsv,
            mapping_term_column="KO",
            annotation_term_column="KO",
        )
        append_branch(
            lines,
            title="KEGG",
            mapping_resource=args.gene2ko_tsv,
            annotation_resource=args.kegg_annotation_tsv,
            mapped_output=args.kegg_mapped_output,
            all_output=args.kegg_all_output,
            significant_output=args.kegg_significant_output,
            plot_output=args.kegg_plot_output,
            term_mapped_label="KEGG pathway-mapped genes",
            term_mapped_count=kegg_pathway_mapped,
        )
    if args.analysis_type in {"ALL", "GO"}:
        go_term_mapped = count_term_mapped_genes(
            args.genelist_txt,
            args.gene2go_tsv,
            args.go_term_tsv,
            mapping_term_column="GO",
            annotation_term_column="GOID",
        )
        append_branch(
            lines,
            title="GO",
            mapping_resource=args.gene2go_tsv,
            annotation_resource=args.go_term_tsv,
            mapped_output=args.go_mapped_output,
            all_output=args.go_all_output,
            significant_output=args.go_significant_output,
            plot_output=args.go_plot_output,
            term_mapped_label="GO term-mapped genes",
            term_mapped_count=go_term_mapped,
        )

    output_path = Path(args.summary_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
