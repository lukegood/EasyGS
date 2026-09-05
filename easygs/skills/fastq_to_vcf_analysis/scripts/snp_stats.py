#!/usr/bin/env python3
"""Generate the SNP statistics and genotype tables used by the original pipeline."""

from __future__ import annotations

import gzip
import sys
from pathlib import Path
from typing import TextIO


def get_base_genotype(gt: str, ref: str, alt_list: list[str]) -> str:
    """Map numeric diploid GT alleles to their reference/alternate bases."""
    if gt in (".", "./.", ".|.", ".,.", ".|"):
        return "NA"

    alleles = gt.replace("|", "/").split("/")
    if len(alleles) != 2:
        return "NA"

    base_map = {"0": ref}
    for index, alt in enumerate(alt_list, start=1):
        base_map[str(index)] = alt if alt != "<NON_REF>" else "X"
    try:
        return f"{base_map[alleles[0]]}{base_map[alleles[1]]}"
    except KeyError:
        return "NA"


def _write_tables(gvcf: TextIO, stats_f: TextIO, geno_f: TextIO) -> None:
    total_samples = 0
    samples: list[str] = []
    stats_f.write(
        "CHROM\tPOS\tEND\tID(chrom_pos_end)\tREF\tALT\tSite_Type\tNA_rate\t"
        "Ref_rate\tHom_nonref_rate\tHet_rate\tMAF\n"
    )

    for line in gvcf:
        line = line.strip()
        if line.startswith("##"):
            continue
        if line.startswith("#CHROM"):
            parts = line.split("\t")
            samples = parts[9:]
            total_samples = len(samples)
            if total_samples == 0:
                raise ValueError("未检测到样本信息")
            geno_f.write("ID\tchrom\tposition\tref\t" + "\t".join(samples) + "\n")
            continue
        if not samples:
            continue

        parts = line.split("\t")
        if len(parts) < 10:
            continue
        chrom = parts[0].strip()
        pos = parts[1].strip()
        ref = parts[3].strip()
        alt_str = parts[4].strip()
        alt_list = [alt.strip() for alt in alt_str.split(",")]
        info = parts[7].strip()
        fmt_fields = parts[8].strip().split(":")
        genotypes = parts[9:]

        end = pos
        if "END=" in info:
            end = info.split("END=")[1].split(";")[0].strip()
        generated_id = f"{chrom}_{pos}_{end}"
        site_type = "Interval_Site" if end != pos else "Single_Site"

        gt_idx = fmt_fields.index("GT") if "GT" in fmt_fields else 0
        sample_gt_list: list[str] = []
        for genotype in genotypes:
            gt_parts = genotype.split(":")
            sample_gt_list.append(gt_parts[gt_idx].strip() if len(gt_parts) > gt_idx else "./.")

        na_count = 0
        hom_ref_count = 0
        hom_nonref_count = 0
        het_count = 0
        allele_counts: dict[int, int] = {}
        total_alleles = 0

        for gt in sample_gt_list:
            if gt in (".", "./.", ".|."):
                na_count += 1
                continue
            alleles = gt.replace("|", "/").split("/")
            if len(alleles) != 2:
                na_count += 1
                continue
            try:
                a1, a2 = int(alleles[0]), int(alleles[1])
            except ValueError:
                na_count += 1
                continue

            allele_counts.setdefault(a1, 0)
            allele_counts.setdefault(a2, 0)
            if a1 == 0 and a2 == 0:
                hom_ref_count += 1
                allele_counts[0] += 2
            elif a1 == a2:
                hom_nonref_count += 1
                allele_counts[a1] += 2
            else:
                het_count += 1
                allele_counts[a1] += 1
                allele_counts[a2] += 1
            total_alleles += 2

        na_rate = na_count / total_samples if total_samples else 0.0
        ref_rate = hom_ref_count / total_samples if total_samples else 0.0
        hom_nonref_rate = hom_nonref_count / total_samples if total_samples else 0.0
        het_rate = het_count / total_samples if total_samples else 0.0
        maf = 0.0
        if total_alleles > 0 and len(allele_counts) > 1:
            maf = min(count / total_alleles for count in allele_counts.values())

        stats_f.write(
            f"{chrom}\t{pos}\t{end}\t{generated_id}\t{ref}\t{alt_str}\t{site_type}\t"
            f"{na_rate:.4f}\t{ref_rate:.4f}\t{hom_nonref_rate:.4f}\t{het_rate:.4f}\t"
            f"{maf:.4f}\n"
        )
        sample_base_geno = [get_base_genotype(gt, ref, alt_list) for gt in sample_gt_list]
        geno_f.write(
            f"{generated_id}\t{chrom}\t{pos}\t{ref}\t" + "\t".join(sample_base_geno) + "\n"
        )


def calculate_gvcf_stats(gvcf_file: Path, output_stats: Path, output_genotypes: Path) -> None:
    """Read a VCF/VCF.GZ and write the two legacy tables."""
    if not gvcf_file.exists():
        raise FileNotFoundError(f"输入文件不存在: {gvcf_file}")
    output_stats.parent.mkdir(parents=True, exist_ok=True)
    output_genotypes.parent.mkdir(parents=True, exist_ok=True)
    if str(gvcf_file).endswith(".gz"):
        source = gzip.open(gvcf_file, "rt", encoding="utf-8")
    else:
        source = gvcf_file.open("r", encoding="utf-8")
    with source as gvcf:
        with output_stats.open("w", encoding="utf-8") as stats_f:
            with output_genotypes.open("w", encoding="utf-8") as geno_f:
                _write_tables(gvcf, stats_f, geno_f)


def main() -> int:
    if len(sys.argv) != 4:
        print("用法: python snp_stats.py <输入VCF> <输出统计文件> <输出基因型文件>")
        return 1
    gvcf_file = Path(sys.argv[1])
    output_stats = Path(sys.argv[2])
    output_genotypes = Path(sys.argv[3])
    calculate_gvcf_stats(gvcf_file, output_stats, output_genotypes)
    print("输出完成！")
    print(f"1. 统计文件：{output_stats}")
    print(f"2. 基因型文件：{output_genotypes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
