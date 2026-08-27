#!/usr/bin/env python3
"""Apply the genotype masking rules used by the original maize pipeline."""

from __future__ import annotations

import gzip
import sys
from pathlib import Path
from typing import TextIO


def get_index(field_list: list[str], target: str) -> int:
    """Return the target index or -1 when it is absent."""
    return field_list.index(target) if target in field_list else -1


def process_vcf(infile: TextIO, outfile: TextIO) -> None:
    """Process VCF content using the original genotype rules."""
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
            if len(sample_fields) != len(fmt_fields):
                filtered_samples.append(":".join(["./."] * len(sample_fields)))
                continue

            new_fields = sample_fields.copy()
            current_gt = new_fields[gt_idx]
            valid_gts = {"0/0", "0/1", "1/0", "1/1"}
            if current_gt not in valid_gts:
                new_fields[gt_idx] = "./."
                filtered_samples.append(":".join(new_fields))
                continue

            if dp_idx != -1:
                dp_val = new_fields[dp_idx]
                if dp_val == "." or (dp_val.isdigit() and int(dp_val) < 5):
                    new_fields[gt_idx] = "./."
                    filtered_samples.append(":".join(new_fields))
                    continue

            if ad_idx != -1 and current_gt in ("0/1", "1/0"):
                ad_val = new_fields[ad_idx]
                if ad_val == "." or "," not in ad_val:
                    new_fields[gt_idx] = "./."
                else:
                    ad_values = ad_val.split(",")
                    if len(ad_values) >= 2 and all(
                        value.isdigit() for value in ad_values[:2]
                    ):
                        ref_ad = int(ad_values[0])
                        alt_ad = int(ad_values[1])
                        if ref_ad < 4 or alt_ad < 4:
                            new_fields[gt_idx] = "./."

            filtered_samples.append(":".join(new_fields))

        if all(sample.split(":")[gt_idx] == "./." for sample in filtered_samples):
            continue
        fields[9:] = filtered_samples
        outfile.write("\t".join(fields) + "\n")


def filter_genotypes(input_vcf: Path, output_vcf: Path) -> None:
    """Read compressed or plain VCF and write the filtered plain VCF."""
    try:
        with gzip.open(input_vcf, "rt", encoding="utf-8") as infile:
            with output_vcf.open("w", encoding="utf-8") as outfile:
                process_vcf(infile, outfile)
    except (gzip.BadGzipFile, OSError):
        with input_vcf.open("r", encoding="utf-8") as infile:
            with output_vcf.open("w", encoding="utf-8") as outfile:
                process_vcf(infile, outfile)


def main() -> int:
    if len(sys.argv) != 3:
        print("用法: python filter_genotype.py <输入 VCF 文件> <输出 VCF 文件>")
        return 1
    input_vcf = Path(sys.argv[1])
    output_vcf = Path(sys.argv[2])
    filter_genotypes(input_vcf, output_vcf)
    print(f"过滤完成！结果已保存到 {output_vcf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
