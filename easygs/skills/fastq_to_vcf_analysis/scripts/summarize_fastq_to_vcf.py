#!/usr/bin/env python3
"""Summarize the outputs of the maize FASTQ-to-VCF pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize FASTQ-to-VCF outputs.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--fastq-dir", required=True)
    parser.add_argument("--reference-fasta", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threads", required=True, type=int)
    parser.add_argument("--parallel-jobs", required=True, type=int)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _size_text(path: Path) -> str:
    if not path.is_file():
        return "missing"
    size = float(path.stat().st_size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def main() -> int:
    args = parse_args()
    fastq_dir = Path(args.fastq_dir)
    output_dir = Path(args.output_dir)
    final_dir = output_dir / "04-Output"
    final_vcf = final_dir / f"{args.project_id}.vcf.gz"
    final_index = final_dir / f"{args.project_id}.vcf.gz.tbi"
    stats_path = final_dir / "snp_statistics.tsv"
    genotypes_path = final_dir / "genotypes.tsv"
    r1_files = sorted(fastq_dir.glob("*_1.fq.gz"))

    lines = [
        "=== FASTQ to VCF ===",
        f"Project ID: {args.project_id}",
        f"FASTQ directory: {fastq_dir}",
        f"Samples: {len(r1_files)}",
        f"Reference FASTA: {args.reference_fasta}",
        f"Threads: {args.threads}",
        f"Parallel jobs: {args.parallel_jobs}",
        f"Output directory: {output_dir}",
        f"QC HTML files: {len(list((output_dir / '01-QC').glob('*_fastp.html')))}",
        f"QC JSON files: {len(list((output_dir / '01-QC').glob('*_fastp.json')))}",
        f"Final VCF.GZ: {final_vcf} ({_size_text(final_vcf)})",
        f"Final VCF index: {final_index} ({_size_text(final_index)})",
        f"SNP statistics: {stats_path} ({_size_text(stats_path)})",
        f"Genotype table: {genotypes_path} ({_size_text(genotypes_path)})",
        f"Logs directory: {output_dir / 'logs'}",
    ]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
