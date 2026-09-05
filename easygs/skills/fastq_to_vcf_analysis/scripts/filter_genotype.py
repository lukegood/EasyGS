#!/usr/bin/env python3
"""Apply configurable diploid genotype masking rules to a VCF."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path
from typing import TextIO


def get_index(field_list: list[str], target: str) -> int:
    """Return the target index or -1 when it is absent."""
    return field_list.index(target) if target in field_list else -1


def _parse_diploid_gt(gt: str) -> tuple[list[int], str] | None:
    if gt in {".", "./.", ".|."}:
        return None
    separator = "|" if "|" in gt else "/"
    tokens = gt.split(separator)
    if len(tokens) != 2 or any(not token.isdigit() for token in tokens):
        return None
    return [int(token) for token in tokens], separator


def _mask_gt(fields: list[str], gt_idx: int, separator: str = "/") -> None:
    fields[gt_idx] = f".{separator}."


def process_vcf(
    infile: TextIO,
    outfile: TextIO,
    *,
    min_depth: int = 5,
    min_allele_depth: int = 4,
) -> None:
    """Mask low-confidence diploid GT values while preserving other FORMAT fields."""
    header_written = False

    for line in infile:
        line = line.rstrip("\n")
        if not line:
            continue
        if line.startswith("##"):
            outfile.write(f"{line}\n")
            continue
        if line.startswith("#CHROM"):
            outfile.write(f"{line}\n")
            header_written = True
            continue
        if not header_written:
            continue

        fields = line.split("\t")
        if len(fields) < 10:
            continue
        fmt_fields = fields[8].split(":")
        samples = fields[9:]
        gt_idx = get_index(fmt_fields, "GT")
        dp_idx = get_index(fmt_fields, "DP")
        ad_idx = get_index(fmt_fields, "AD")
        if gt_idx == -1:
            continue

        filtered_samples: list[str] = []
        for sample in samples:
            sample_fields = sample.split(":")
            if len(sample_fields) < len(fmt_fields):
                sample_fields.extend(["."] * (len(fmt_fields) - len(sample_fields)))

            new_fields = sample_fields.copy()
            current_gt = new_fields[gt_idx]
            parsed_gt = _parse_diploid_gt(current_gt)
            if parsed_gt is None:
                _mask_gt(new_fields, gt_idx, "|" if "|" in current_gt else "/")
                filtered_samples.append(":".join(new_fields))
                continue
            alleles, separator = parsed_gt

            if dp_idx != -1 and min_depth > 0:
                dp_val = new_fields[dp_idx]
                if not dp_val.isdigit() or int(dp_val) < min_depth:
                    _mask_gt(new_fields, gt_idx, separator)
                    filtered_samples.append(":".join(new_fields))
                    continue

            if ad_idx != -1 and min_allele_depth > 0 and len(set(alleles)) > 1:
                ad_val = new_fields[ad_idx]
                ad_values = ad_val.split(",")
                called_depths = [
                    ad_values[allele] if allele < len(ad_values) else "." for allele in set(alleles)
                ]
                if any(
                    not depth.isdigit() or int(depth) < min_allele_depth
                    for depth in called_depths
                ):
                    _mask_gt(new_fields, gt_idx, separator)

            filtered_samples.append(":".join(new_fields))

        if all(
            _parse_diploid_gt(sample.split(":")[gt_idx]) is None
            for sample in filtered_samples
        ):
            continue
        fields[9:] = filtered_samples
        outfile.write("\t".join(fields) + "\n")


def filter_genotypes(
    input_vcf: Path,
    output_vcf: Path,
    *,
    min_depth: int = 5,
    min_allele_depth: int = 4,
) -> None:
    """Read compressed or plain VCF and write the filtered plain VCF."""
    try:
        with gzip.open(input_vcf, "rt", encoding="utf-8") as infile:
            with output_vcf.open("w", encoding="utf-8") as outfile:
                process_vcf(
                    infile,
                    outfile,
                    min_depth=min_depth,
                    min_allele_depth=min_allele_depth,
                )
    except (gzip.BadGzipFile, OSError):
        with input_vcf.open("r", encoding="utf-8") as infile:
            with output_vcf.open("w", encoding="utf-8") as outfile:
                process_vcf(
                    infile,
                    outfile,
                    min_depth=min_depth,
                    min_allele_depth=min_allele_depth,
                )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mask low-confidence diploid VCF genotypes.")
    parser.add_argument("input_vcf")
    parser.add_argument("output_vcf")
    parser.add_argument("--min-depth", type=int, default=5)
    parser.add_argument("--min-allele-depth", type=int, default=4)
    args = parser.parse_args()
    if args.min_depth < 0 or args.min_allele_depth < 0:
        parser.error("depth thresholds must be non-negative")
    return args


def main() -> int:
    args = parse_args()
    input_vcf = Path(args.input_vcf)
    output_vcf = Path(args.output_vcf)
    filter_genotypes(
        input_vcf,
        output_vcf,
        min_depth=args.min_depth,
        min_allele_depth=args.min_allele_depth,
    )
    print(f"过滤完成！结果已保存到 {output_vcf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
