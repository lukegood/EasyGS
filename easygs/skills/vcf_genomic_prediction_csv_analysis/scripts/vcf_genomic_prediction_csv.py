#!/usr/bin/env python3
"""Prepare genomic-prediction-ready 0/1/2 genotype CSV matrices from VCF."""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import shutil
import tempfile
import uuid
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a 0/1/2 genotype CSV matrix for genomic prediction methods."
    )
    parser.add_argument("--vcf", required=True, help="Input .vcf or .vcf.gz file.")
    parser.add_argument("--output", required=True, help="Final genomic prediction genotype CSV path.")
    parser.add_argument("--summary-output", required=True, help="Summary text output path.")
    parser.add_argument("--marker-csv", required=True, help="Intermediate marker x sample CSV path.")
    parser.add_argument("--transpose", choices=["0", "1"], default="1", help="Transpose final CSV.")
    parser.add_argument(
        "--keep-marker-csv",
        choices=["0", "1"],
        default="0",
        help="Keep intermediate marker x sample CSV when transposing.",
    )
    return parser.parse_args()


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def encode_genotype(raw_value: str) -> int | None:
    genotype = raw_value.split(":", 1)[0].strip()
    if genotype in {"./.", ".|.", "./", ".|", "."}:
        raise ValueError("missing")
    if genotype in {"0/0", "0|0"}:
        return 0
    if genotype in {"0/1", "1/0", "0|1", "1|0"}:
        return 1
    if genotype in {"1/1", "1|1"}:
        return 2
    return None


def write_marker_matrix(vcf_path: Path, marker_csv_path: Path) -> dict[str, int]:
    marker_csv_path.parent.mkdir(parents=True, exist_ok=True)

    samples: list[str] = []
    kept_variant_count = 0
    skipped_missing_count = 0
    skipped_unsupported_count = 0

    with open_text(vcf_path) as handle, marker_csv_path.open(
        "w", encoding="utf-8", newline=""
    ) as output_handle:
        writer = csv.writer(output_handle)
        header_seen = False

        for line in handle:
            line = line.rstrip("\n")
            if not line or line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                columns = line.split("\t")
                if len(columns) < 10:
                    raise ValueError("VCF header must contain at least one sample column.")
                samples = columns[9:]
                writer.writerow(["ID", *samples])
                header_seen = True
                continue
            if line.startswith("#"):
                continue
            if not header_seen:
                raise ValueError("VCF header line (#CHROM ...) was not found before variants.")

            fields = line.split("\t")
            if len(fields) < 10:
                skipped_unsupported_count += 1
                continue

            marker_id = fields[2] or f"{fields[0]}:{fields[1]}"
            sample_values = fields[9:]
            if len(sample_values) != len(samples):
                skipped_unsupported_count += 1
                continue

            encoded_values: list[int] = []
            skip_for_missing = False
            skip_for_unsupported = False
            for value in sample_values:
                try:
                    encoded = encode_genotype(value)
                except ValueError:
                    skip_for_missing = True
                    break
                if encoded is None:
                    skip_for_unsupported = True
                    break
                encoded_values.append(encoded)

            if skip_for_missing:
                skipped_missing_count += 1
                continue
            if skip_for_unsupported:
                skipped_unsupported_count += 1
                continue

            writer.writerow([marker_id, *encoded_values])
            kept_variant_count += 1

    if not samples:
        raise ValueError("No VCF sample columns were found.")

    return {
        "sample_count": len(samples),
        "kept_variant_count": kept_variant_count,
        "skipped_missing_count": skipped_missing_count,
        "skipped_unsupported_count": skipped_unsupported_count,
    }


def transpose_csv(input_file: Path, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = input_file.parent / f"transpose_temp_{uuid.uuid4()}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        chunk_size = 50000
        max_open = 100
        temp_files: list[Path] = []
        with input_file.open("r", encoding="utf-8", newline="") as fin:
            reader = csv.reader(fin)
            chunk: list[list[str]] = []
            chunk_index = 0
            for row in reader:
                chunk.append(row)
                if len(chunk) == chunk_size:
                    temp_files.append(write_transposed_chunk(chunk, temp_dir, chunk_index))
                    chunk_index += 1
                    chunk = []
            if chunk:
                temp_files.append(write_transposed_chunk(chunk, temp_dir, chunk_index))

        current_files = temp_files
        while len(current_files) > 1:
            current_files = merge_transposed_chunks(current_files, temp_dir, max_open)

        if not current_files:
            raise ValueError("No rows were available to transpose.")
        os.replace(current_files[0], output_file)
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def write_transposed_chunk(rows: list[list[str]], temp_dir: Path, chunk_index: int) -> Path:
    fd, temp_name = tempfile.mkstemp(prefix=f"chunk_{chunk_index}_", suffix=".csv", dir=temp_dir)
    temp_path = Path(temp_name)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerows(zip(*rows))
    return temp_path


def merge_transposed_chunks(file_list: list[Path], temp_dir: Path, max_open: int) -> list[Path]:
    merged_files: list[Path] = []
    for index in range(0, len(file_list), max_open):
        group = file_list[index : index + max_open]
        fd, merged_name = tempfile.mkstemp(prefix="merged_", suffix=".csv", dir=temp_dir)
        merged_path = Path(merged_name)
        handles = []
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fout:
                writer = csv.writer(fout)
                handles = [path.open("r", encoding="utf-8", newline="") for path in group]
                readers = [csv.reader(handle) for handle in handles]
                while True:
                    row_parts: list[list[str]] = []
                    for reader in readers:
                        try:
                            row_parts.append(next(reader))
                        except StopIteration:
                            row_parts = []
                            break
                    if not row_parts:
                        break
                    merged_row: list[str] = []
                    for part in row_parts:
                        merged_row.extend(part)
                    writer.writerow(merged_row)
        finally:
            for handle in handles:
                handle.close()
            for path in group:
                if path.exists():
                    path.unlink()
        merged_files.append(merged_path)
    return merged_files


def write_summary(
    *,
    input_vcf: Path,
    output_csv: Path,
    marker_csv: Path,
    summary_output: Path,
    transpose: bool,
    keep_marker_csv: bool,
    counts: dict[str, int],
) -> None:
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    marker_line = str(marker_csv) if marker_csv.exists() else "removed"
    lines = [
        "=== VCF to genomic prediction genotype CSV summary ===",
        f"Input VCF: {input_vcf}",
        f"Genomic prediction genotype CSV: {output_csv}",
        f"Marker CSV: {marker_line}",
        f"Transposed output: {transpose}",
        f"Kept marker CSV: {keep_marker_csv}",
        "",
        "Encoding:",
        "- 0: 0/0 or 0|0",
        "- 1: 0/1, 1/0, 0|1, or 1|0",
        "- 2: 1/1 or 1|1",
        "",
        f"Sample count: {counts['sample_count']}",
        f"Variants kept: {counts['kept_variant_count']}",
        f"Variants skipped for missing genotypes: {counts['skipped_missing_count']}",
        f"Variants skipped for unsupported genotypes: {counts['skipped_unsupported_count']}",
    ]
    summary_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    vcf_path = Path(args.vcf)
    output_path = Path(args.output)
    marker_csv_path = Path(args.marker_csv)
    summary_output = Path(args.summary_output)
    transpose = args.transpose == "1"
    keep_marker_csv = args.keep_marker_csv == "1"

    if not (str(vcf_path).endswith(".vcf") or str(vcf_path).endswith(".vcf.gz")):
        raise ValueError(f"VCF input must end with .vcf or .vcf.gz: {vcf_path}")

    counts = write_marker_matrix(vcf_path, marker_csv_path)
    if transpose:
        transpose_csv(marker_csv_path, output_path)
        if not keep_marker_csv and marker_csv_path.exists():
            marker_csv_path.unlink()
    else:
        if marker_csv_path != output_path:
            os.replace(marker_csv_path, output_path)
            marker_csv_path = output_path

    write_summary(
        input_vcf=vcf_path,
        output_csv=output_path,
        marker_csv=marker_csv_path,
        summary_output=summary_output,
        transpose=transpose,
        keep_marker_csv=keep_marker_csv,
        counts=counts,
    )

    print("VCF to genomic prediction genotype CSV conversion completed.")
    print(f"Genomic prediction genotype CSV: {output_path}")
    print(f"Summary file: {summary_output}")


if __name__ == "__main__":
    main()
