#!/usr/bin/env python3
"""Summarize VCF format-conversion outputs."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize VCF format-conversion outputs.")
    parser.add_argument("--input-label", required=True, choices=["vcf", "bfile", "ped"], help="Input type.")
    parser.add_argument("--input-path", required=True, help="Input path or prefix.")
    parser.add_argument("--out-prefix", required=True, help="Output prefix used by PLINK.")
    parser.add_argument("--target-format", required=True, choices=["bed", "ped", "vcf"], help="Target format family.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    parser.add_argument("--double-id", required=True, help="Whether --double-id was enabled.")
    parser.add_argument("--allow-extra-chr", required=True, help="Whether --allow-extra-chr was enabled.")
    return parser.parse_args()


def build_expected_outputs(prefix: Path, target_format: str) -> list[Path]:
    if target_format == "bed":
        suffixes = [".bed", ".bim", ".fam", ".log", ".nosex"]
    elif target_format == "ped":
        suffixes = [".ped", ".map", ".log"]
    else:
        suffixes = [".vcf", ".log", ".nosex"]
    return [prefix.with_suffix(suffix) for suffix in suffixes]


def main() -> None:
    args = parse_args()
    out_prefix = Path(args.out_prefix)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    expected_outputs = build_expected_outputs(out_prefix, args.target_format)
    existing_outputs = [path for path in expected_outputs if path.exists()]
    missing_outputs = [path for path in expected_outputs if not path.exists()]

    format_label = {
        "bed": "BED/BIM/FAM",
        "ped": "PED/MAP",
        "vcf": "VCF",
    }[args.target_format]
    lines = [
        "VCF format conversion summary",
        f"Input ({args.input_label}): {Path(args.input_path)}",
        f"Target format: {args.target_format} ({format_label})",
        f"Output prefix: {out_prefix}",
        "",
        "Applied options:",
    ]

    if args.target_format == "bed" and args.input_label == "vcf":
        lines.append(f"- --double-id: {'yes' if args.double_id == '1' else 'no'}")
    elif args.target_format == "bed" and args.input_label == "ped":
        lines.append("- PLINK mode: --file <prefix> --make-bed")
    elif args.target_format == "ped":
        lines.append(f"- --allow-extra-chr: {'yes' if args.allow_extra_chr == '1' else 'no'}")
    else:
        lines.append("- PLINK mode: --bfile <prefix> --export vcf")

    lines.extend(
        [
        "",
        "Generated files:",
        ]
    )

    if existing_outputs:
        lines.extend(f"- {path}" for path in existing_outputs)
    else:
        lines.append("- No expected output files were found.")

    if missing_outputs:
        lines.extend(["", "Missing expected files:"])
        lines.extend(f"- {path}" for path in missing_outputs)

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
