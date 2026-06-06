#!/usr/bin/env python3
"""Summarize bcftools-based VCF variant extraction output."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize VCF variant extraction output.")
    parser.add_argument("--vcf", required=True, help="Input VCF path.")
    parser.add_argument("--variant-ids-input-label", required=True, help="Original variant ID source label.")
    parser.add_argument("--variant-ids", required=True, help="Normalized variant ID list path.")
    parser.add_argument("--output-vcf", required=True, help="Extracted output VCF path.")
    parser.add_argument("--output", required=True, help="Summary output path.")
    return parser.parse_args()


def _read_variant_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _read_extracted_variant_ids(path: Path, limit: int = 10) -> tuple[int, list[str]]:
    if not path.exists():
        return 0, []
    count = 0
    preview: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            count += 1
            if len(preview) < limit:
                fields = line.rstrip("\n").split("\t")
                preview.append(fields[2] if len(fields) > 2 else "n/a")
    return count, preview


def main() -> None:
    args = parse_args()
    variant_ids_path = Path(args.variant_ids)
    output_vcf_path = Path(args.output_vcf)
    summary_path = Path(args.output)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    requested_ids = _read_variant_ids(variant_ids_path)
    extracted_count, extracted_preview = _read_extracted_variant_ids(output_vcf_path)

    lines = [
        "=== VCF 位点提取 ===",
        f"输入 VCF: {Path(args.vcf)}",
        f"位点列表来源: {args.variant_ids_input_label}",
        f"标准化位点列表: {variant_ids_path}",
        f"输出 VCF: {output_vcf_path}",
        f"请求提取位点数: {len(requested_ids)}",
        f"输出 VCF 位点数: {extracted_count}",
    ]
    if extracted_preview:
        lines.append("输出 VCF 前几个位点 ID:")
        lines.extend(extracted_preview)

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
