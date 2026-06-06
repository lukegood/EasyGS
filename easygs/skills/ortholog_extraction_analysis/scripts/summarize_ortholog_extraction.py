#!/usr/bin/env python3
"""Summarize ortholog extraction outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize ortholog extraction outputs.")
    parser.add_argument("--genelist-txt", required=True)
    parser.add_argument("--ortholog-matrix-tsv", required=True)
    parser.add_argument("--output-tsv", required=True)
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
    genelist_path = Path(args.genelist_txt)
    matrix_path = Path(args.ortholog_matrix_tsv)
    output_path = Path(args.output_tsv)
    summary_path = Path(args.summary_output)

    requested_genes = _read_nonempty_lines(genelist_path)
    matched_rows = _read_nonempty_lines(output_path)
    matched_maize_genes = []
    for row in matched_rows:
        first_field = row.split("\t", 1)[0].strip()
        if first_field and first_field != "Maize":
            matched_maize_genes.append(first_field)

    unique_requested = list(dict.fromkeys(requested_genes))
    unique_matched = list(dict.fromkeys(matched_maize_genes))
    missing_count = max(len(unique_requested) - len(unique_matched), 0)

    lines = [
        "=== 同源基因提取 ===",
        f"Gene list TXT: {genelist_path}",
        f"Ortholog matrix TSV: {matrix_path}",
        f"Output TSV: {output_path}",
        f"Requested genes: {len(requested_genes)}",
        f"Unique requested genes: {len(unique_requested)}",
        f"Matched rows: {len(matched_rows)}",
        f"Matched maize genes: {len(unique_matched)}",
        f"Missing genes (by unique maize IDs): {missing_count}",
    ]
    if matched_rows:
        lines.append("First matched rows:")
        for row in matched_rows[:5]:
            lines.append(f"- {row}")

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
