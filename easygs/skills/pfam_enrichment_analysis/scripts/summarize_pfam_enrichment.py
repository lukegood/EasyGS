#!/usr/bin/env python3
"""Summarize PFAM/domain enrichment outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PFAM/domain enrichment outputs.")
    parser.add_argument("--genelist-txt", required=True, help="Input gene list TXT.")
    parser.add_argument("--longest-cds-txt", required=True, help="Built-in maize longest-CDS mapping TXT.")
    parser.add_argument("--proteins-tsv", required=True, help="Built-in maize protein annotation TSV.")
    parser.add_argument("--background-protein-txt", required=True, help="Optional background protein TXT.")
    parser.add_argument("--annotation-source", required=True, help="Selected annotation source.")
    parser.add_argument("--min-count-in-candidates", required=True, help="Significant-count threshold.")
    parser.add_argument("--p-adjust-method", required=True, help="P-adjust method.")
    parser.add_argument("--fdr-cutoff", required=True, help="FDR cutoff.")
    parser.add_argument("--protlist-output", required=True, help="Generated protlist.txt.")
    parser.add_argument("--protlist-stranno-output", required=True, help="Generated protlist.stranno.tsv.")
    parser.add_argument("--all-enrichment-csv-output", required=True, help="All enrichment CSV.")
    parser.add_argument("--sig-enrichment-csv-output", required=True, help="Significant enrichment CSV.")
    parser.add_argument("--summary-output", required=True, help="Summary output path.")
    return parser.parse_args()


def _count_nonempty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for line in handle if line.strip())


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def _top_pfam_rows(path: Path, limit: int = 5) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pfam = (row.get("pfam") or "").strip()
            count_k = (row.get("k") or "").strip()
            p_adj = (row.get("p_adj") or "").strip()
            if pfam:
                rows.append((pfam, count_k, p_adj))
            if len(rows) >= limit:
                break
    return rows


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    protlist_count = _count_nonempty_lines(Path(args.protlist_output))
    stranno_rows = _count_nonempty_lines(Path(args.protlist_stranno_output))
    all_rows = _count_rows(Path(args.all_enrichment_csv_output))
    sig_rows = _count_rows(Path(args.sig_enrichment_csv_output))
    top_domains = _top_pfam_rows(Path(args.all_enrichment_csv_output))

    lines = [
        "=== PFAM/结构域富集 ===",
        f"Gene list TXT: {args.genelist_txt}",
        f"Maize longest CDS resource: {args.longest_cds_txt}",
        f"Maize proteins TSV resource: {args.proteins_tsv}",
        f"Background protein TXT: {args.background_protein_txt or 'default(all annotated proteins)'}",
        f"Annotation source: {args.annotation_source}",
        f"Min count in candidates: {args.min_count_in_candidates}",
        f"P adjust method: {args.p_adjust_method}",
        f"FDR cutoff: {args.fdr_cutoff}",
        f"protlist.txt: {args.protlist_output}",
        f"protlist.stranno.tsv: {args.protlist_stranno_output}",
        f"All enrichment CSV: {args.all_enrichment_csv_output}",
        f"Significant enrichment CSV: {args.sig_enrichment_csv_output}",
        f"Candidate proteins: {protlist_count}",
        f"Annotation rows for candidates: {stranno_rows}",
        f"All enrichment rows: {all_rows}",
        f"Significant enrichment rows: {sig_rows}",
    ]

    if top_domains:
        lines.append("Top domains:")
        for pfam, count_k, p_adj in top_domains:
            lines.append(f"- {pfam}: k={count_k}, p_adj={p_adj}")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
