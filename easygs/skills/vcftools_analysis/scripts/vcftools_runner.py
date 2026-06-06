#!/usr/bin/env python3
"""Run vcftools with EasyGS-managed input/output paths."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

MANAGED_FLAGS = {"--vcf", "--gzvcf", "--out"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vcftools with structured arguments.")
    parser.add_argument("--vcf", required=True, help="Input .vcf or .vcf.gz file.")
    parser.add_argument("--out-prefix", required=True, help="vcftools output prefix path.")
    parser.add_argument("--summary-output", required=True, help="Summary text output path.")
    parser.add_argument(
        "--args-json",
        required=True,
        help="JSON array of vcftools argument tokens managed by EasyGS.",
    )
    return parser.parse_args()


def load_vcftools_args(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("--args-json must be a JSON array of strings.") from exc
    if not isinstance(value, list) or not value:
        raise ValueError("--args-json must be a non-empty JSON array of strings.")
    tokens = [str(item) for item in value]
    if tokens and tokens[0] == "vcftools":
        raise ValueError("args must contain only vcftools option tokens, not the 'vcftools' command.")
    forbidden = [token for token in tokens if is_managed_flag_token(token)]
    if forbidden:
        joined = ", ".join(forbidden)
        raise ValueError(f"Do not include EasyGS-managed vcftools flags in args: {joined}")
    return tokens


def is_managed_flag_token(token: str) -> bool:
    if token in MANAGED_FLAGS:
        return True
    return any(token.startswith(f"{flag}=") for flag in MANAGED_FLAGS)


def collect_output_files(prefix_path: Path, summary_path: Path) -> list[Path]:
    parent = prefix_path.parent
    prefix_name = prefix_path.name
    files = [
        path
        for path in parent.glob(f"{prefix_name}*")
        if path.is_file() and path.resolve() != summary_path.resolve()
    ]
    return sorted(files)


def write_summary(
    *,
    summary_path: Path,
    vcf_path: Path,
    out_prefix: Path,
    vcftools_args: list[str],
    command: list[str],
    output_files: list[Path],
) -> None:
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "=== vcftools run summary ===",
        f"Input VCF: {vcf_path}",
        f"Output prefix: {out_prefix}",
        f"vcftools args: {' '.join(vcftools_args)}",
        f"Command: {' '.join(command)}",
        "",
        "Generated files:",
    ]
    if output_files:
        lines.extend(f"- {path}" for path in output_files)
    else:
        lines.append("- none detected")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    vcf_path = Path(args.vcf)
    out_prefix = Path(args.out_prefix)
    summary_path = Path(args.summary_output)
    vcftools_args = load_vcftools_args(args.args_json)

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    if str(vcf_path).endswith(".vcf.gz"):
        input_flag = "--gzvcf"
    elif str(vcf_path).endswith(".vcf"):
        input_flag = "--vcf"
    else:
        raise ValueError(f"VCF input must end with .vcf or .vcf.gz: {vcf_path}")

    command = ["vcftools", input_flag, str(vcf_path), *vcftools_args, "--out", str(out_prefix)]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    output_files = collect_output_files(out_prefix, summary_path)
    write_summary(
        summary_path=summary_path,
        vcf_path=vcf_path,
        out_prefix=out_prefix,
        vcftools_args=vcftools_args,
        command=command,
        output_files=output_files,
    )
    print("vcftools run completed.")
    print(f"Output prefix: {out_prefix}")
    print(f"Summary file: {summary_path}")
    if output_files:
        print("Generated files:")
        for path in output_files:
            print(path)


if __name__ == "__main__":
    main()
