#!/usr/bin/env python3
"""Summarize PLINK sample keep/remove outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


FORMAT_HINT = (
    "Two-column FID/IID file. Example:\n"
    "MG_890 MG_890\n"
    "MG_1254 MG_1254\n"
    "MG_689 MG_689"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK sample keep/remove outputs.")
    parser.add_argument("--action", required=True, choices=["keep", "remove"], help="Subset action.")
    parser.add_argument("--input-bfile", required=True, help="Input PLINK BFILE prefix.")
    parser.add_argument("--original-sample-list", required=True, help="Original sample list path.")
    parser.add_argument("--sample-list", required=True, help="Normalized sample list path.")
    parser.add_argument("--subset-prefix", required=True, help="Subset PED/MAP output prefix.")
    parser.add_argument("--bed-prefix", required=True, help="Intermediate BED output prefix.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _count_non_empty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())


def main() -> None:
    args = parse_args()
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    subset_prefix = Path(args.subset_prefix)
    bed_prefix = Path(args.bed_prefix)
    normalized_sample_list = Path(args.sample_list)
    fam_path = bed_prefix.with_suffix(".fam")

    requested_count = _count_non_empty_lines(normalized_sample_list)
    retained_count = _count_non_empty_lines(fam_path)
    retained_label = str(retained_count) if fam_path.exists() else "n/a"

    lines = [
        "Sample subset summary",
        f"Action: {args.action}",
        f"Input BFILE: {Path(args.input_bfile)}",
        f"Original sample list: {Path(args.original_sample_list)}",
        f"Normalized sample list: {normalized_sample_list}",
        f"Requested sample rows: {requested_count}",
        f"Resulting sample count: {retained_label}",
        "",
        "Required sample list format:",
        FORMAT_HINT,
        "",
        "Generated files:",
        f"- {subset_prefix}.ped",
        f"- {subset_prefix}.map",
        f"- {bed_prefix}.bed",
        f"- {bed_prefix}.bim",
        f"- {bed_prefix}.fam",
        f"- {subset_prefix}.vcf",
    ]

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
