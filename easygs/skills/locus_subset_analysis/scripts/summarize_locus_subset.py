#!/usr/bin/env python3
"""Summarize PLINK locus keep/remove outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


FORMAT_HINT = (
    "One locus ID per line. Example:\n"
    "chr1.s_667117\n"
    "chr1.s_915373\n"
    "chr1.s_1022873\n"
    "chr1.s_1065915\n"
    "chr1.s_1069916\n"
    "chr1.s_1102676\n"
    "chr1.s_1154593\n"
    "chr1.s_1172097\n"
    "chr1.s_1173275\n"
    "chr1.s_1240840"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PLINK locus keep/remove outputs.")
    parser.add_argument("--action", required=True, choices=["extract", "exclude"], help="Subset action.")
    parser.add_argument("--input-bfile", required=True, help="Input PLINK BFILE prefix.")
    parser.add_argument("--loci-input-label", required=True, help="Original loci input description.")
    parser.add_argument("--loci-list", required=True, help="Normalized loci list path.")
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
    normalized_loci_list = Path(args.loci_list)
    map_path = subset_prefix.with_suffix(".map")
    bim_path = bed_prefix.with_suffix(".bim")

    requested_count = _count_non_empty_lines(normalized_loci_list)
    if map_path.exists():
        resulting_label = str(_count_non_empty_lines(map_path))
    elif bim_path.exists():
        resulting_label = str(_count_non_empty_lines(bim_path))
    else:
        resulting_label = "n/a"

    lines = [
        "Locus subset summary",
        f"Action: {args.action}",
        f"Input BFILE: {Path(args.input_bfile)}",
        f"Loci input: {args.loci_input_label}",
        f"Normalized loci list: {normalized_loci_list}",
        f"Requested loci rows: {requested_count}",
        f"Resulting locus count: {resulting_label}",
        "",
        "Required loci list format:",
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
