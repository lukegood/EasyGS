#!/usr/bin/env python3
"""Summarize GO/KEGG gene function annotation outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize gene function annotation outputs.")
    parser.add_argument("--genelist-txt", required=True, help="Input gene list TXT.")
    parser.add_argument("--entrez-map-csv", required=True, help="Built-in gene-to-ENTREZ CSV path.")
    parser.add_argument("--gene-column", required=True, help="Gene column used in the CSV.")
    parser.add_argument("--entrez-column", required=True, help="ENTREZ column used in the CSV.")
    parser.add_argument("--annotationhub-id", required=True, help="AnnotationHub OrgDb resource ID.")
    parser.add_argument("--kegg-organism", required=True, help="KEGG organism code.")
    parser.add_argument("--go-ontology", required=True, help="GO ontology.")
    parser.add_argument("--kegg-pvalue-threshold", required=True, help="KEGG p-value filter.")
    parser.add_argument("--go-pvalue-threshold", required=True, help="GO p-value filter.")
    parser.add_argument("--kegg-txt-output", required=True, help="KEGG result table.")
    parser.add_argument("--kegg-png-output", required=True, help="KEGG figure.")
    parser.add_argument("--go-txt-output", required=True, help="GO result table.")
    parser.add_argument("--go-png-output", required=True, help="GO figure.")
    parser.add_argument("--mapping-summary-output", required=True, help="Mapping summary TSV.")
    parser.add_argument("--summary-output", required=True, help="Human-readable summary output.")
    return parser.parse_args()


def _read_metrics(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    if not path.exists():
        return metrics
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            metric = (row.get("metric") or "").strip()
            value = (row.get("value") or "").strip()
            if metric:
                metrics[metric] = value
    return metrics


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def _top_descriptions(path: Path, limit: int = 3) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        items: list[str] = []
        for row in reader:
            description = (row.get("Description") or "").strip()
            if description:
                items.append(description)
            if len(items) >= limit:
                break
    return items


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = _read_metrics(Path(args.mapping_summary_output))
    kegg_rows = _count_rows(Path(args.kegg_txt_output))
    go_rows = _count_rows(Path(args.go_txt_output))
    kegg_top = _top_descriptions(Path(args.kegg_txt_output))
    go_top = _top_descriptions(Path(args.go_txt_output))

    lines = [
        "=== 基因功能注释 ===",
        f"Gene list TXT: {args.genelist_txt}",
        f"Built-in ENTREZ map CSV: {args.entrez_map_csv}",
        f"Gene column: {args.gene_column}",
        f"ENTREZ column: {args.entrez_column}",
        f"AnnotationHub ID: {args.annotationhub_id}",
        f"KEGG organism: {args.kegg_organism}",
        f"GO ontology: {args.go_ontology}",
        f"KEGG p-value threshold: {args.kegg_pvalue_threshold}",
        f"GO p-value threshold: {args.go_pvalue_threshold}",
        f"Input gene rows: {metrics.get('input_gene_rows', '0')}",
        f"Unique input genes: {metrics.get('unique_input_genes', '0')}",
        f"Mapped input genes: {metrics.get('mapped_input_genes', '0')}",
        f"Mapped ENTREZ IDs: {metrics.get('mapped_entrez_ids', '0')}",
        f"Unmapped input genes: {metrics.get('unmapped_input_genes', '0')}",
        f"OrgDb status: {metrics.get('orgdb_status', 'n/a')}",
        f"KEGG status: {metrics.get('kegg_status', 'n/a')}",
        f"GO status: {metrics.get('go_status', 'n/a')}",
        f"KEGG result rows: {kegg_rows}",
        f"GO result rows: {go_rows}",
        f"KEGG PNG exists: {'yes' if Path(args.kegg_png_output).exists() else 'no'}",
        f"GO PNG exists: {'yes' if Path(args.go_png_output).exists() else 'no'}",
    ]

    if kegg_top:
        lines.append("Top KEGG terms:")
        for item in kegg_top:
            lines.append(f"- {item}")

    if go_top:
        lines.append("Top GO terms:")
        for item in go_top:
            lines.append(f"- {item}")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
