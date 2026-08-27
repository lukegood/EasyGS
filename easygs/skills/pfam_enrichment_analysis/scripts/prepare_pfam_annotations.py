#!/usr/bin/env python3
"""Stream large wheat/rice InterProScan TSVs into compact PFAM inputs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_TRANSCRIPT_SUFFIX = re.compile(r"\.[0-9]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare direct gene-to-PFAM inputs.")
    parser.add_argument("--genelist-txt", required=True)
    parser.add_argument("--proteins-tsv", required=True)
    parser.add_argument("--annotation-source", required=True)
    parser.add_argument("--protlist-output", required=True)
    parser.add_argument("--protlist-stranno-output", required=True)
    parser.add_argument("--source-annotation-tsv-output", required=True)
    return parser.parse_args()


def _normalize_id(value: str) -> str:
    return _TRANSCRIPT_SUFFIX.sub("", value.strip().lstrip("\ufeff"))


def _read_candidates(path: Path) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            gene = _normalize_id(raw)
            if gene and gene not in seen:
                candidates.append(gene)
                seen.add(gene)
    return candidates


def main() -> int:
    args = parse_args()
    candidates = _read_candidates(Path(args.genelist_txt))
    candidate_set = set(candidates)
    annotation_path = Path(args.proteins_tsv)
    protlist_path = Path(args.protlist_output)
    candidate_annotation_path = Path(args.protlist_stranno_output)
    source_annotation_path = Path(args.source_annotation_tsv_output)

    for path in (protlist_path, candidate_annotation_path, source_annotation_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    protlist_path.write_text("".join(f"{gene}\n" for gene in candidates), encoding="utf-8")

    candidate_rows = 0
    source_rows = 0
    with (
        annotation_path.open("r", encoding="utf-8", errors="replace") as annotation,
        candidate_annotation_path.open("w", encoding="utf-8") as candidate_output,
        source_annotation_path.open("w", encoding="utf-8") as source_output,
    ):
        for raw in annotation:
            fields = raw.rstrip("\r\n").split("\t", 5)
            if len(fields) < 5:
                continue
            gene = _normalize_id(fields[0])
            if not gene:
                continue

            if gene in candidate_set:
                first_tab = raw.find("\t")
                suffix = raw[first_tab:] if first_tab >= 0 else "\n"
                candidate_output.write(gene + suffix)
                if raw and not raw.endswith(("\n", "\r")):
                    candidate_output.write("\n")
                candidate_rows += 1

            analysis = fields[3].strip()
            domain = fields[4].strip()
            if analysis == args.annotation_source and domain not in {"", "-"}:
                source_output.write(
                    "\t".join((gene, fields[1], fields[2], analysis, domain)) + "\n"
                )
                source_rows += 1

    print(
        f"Prepared {len(candidates)} candidate IDs, {candidate_rows} candidate annotation "
        f"rows, and {source_rows} {args.annotation_source} rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
