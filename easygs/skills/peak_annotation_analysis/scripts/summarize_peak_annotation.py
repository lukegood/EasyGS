#!/usr/bin/env python3
"""Summarize peak/locus structural annotation outputs."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize peak annotation outputs.")
    parser.add_argument("--gff3", required=True, help="Input GFF3/GFF path.")
    parser.add_argument("--bed", required=True, help="Input BED path.")
    parser.add_argument("--output-tsv", required=True, help="Annotation TSV output.")
    parser.add_argument("--output-png", required=True, help="Annotation PNG output.")
    parser.add_argument("--summary-output", required=True, help="Summary output path.")
    parser.add_argument("--tss-upstream", required=True, type=int, help="Upstream TSS window.")
    parser.add_argument("--tss-downstream", required=True, type=int, help="Downstream TSS window.")
    return parser.parse_args()


def _collect_annotation_counts(path: Path) -> tuple[int, Counter[str]]:
    if not path.exists():
        return 0, Counter()
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        counts: Counter[str] = Counter()
        rows = 0
        for row in reader:
            rows += 1
            label = (row.get("annotation") or "").strip()
            if label:
                counts[label] += 1
    return rows, counts


def main() -> None:
    args = parse_args()
    output_tsv = Path(args.output_tsv)
    output_png = Path(args.output_png)
    summary_path = Path(args.summary_output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    row_count, annotation_counts = _collect_annotation_counts(output_tsv)
    lines = [
        "=== 位点结构注释 ===",
        f"GFF3: {args.gff3}",
        f"BED: {args.bed}",
        f"TSS region: -{args.tss_upstream}bp to +{args.tss_downstream}bp",
        f"Annotation TSV: {output_tsv}",
        f"Annotation PNG: {output_png}",
        f"Annotated rows: {row_count}",
        f"PNG exists: {'yes' if output_png.exists() else 'no'}",
    ]

    if annotation_counts:
        lines.append("Top annotation classes:")
        for label, count in annotation_counts.most_common(5):
            lines.append(f"- {label}: {count}")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
