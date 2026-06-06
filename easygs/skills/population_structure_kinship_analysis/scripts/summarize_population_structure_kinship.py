#!/usr/bin/env python3
"""Summarize the combined population-structure and kinship workflow."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize the combined population workflow.")
    parser.add_argument("--input-bfile", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ld-prune-prefix", required=True)
    parser.add_argument("--ld-bfile-prefix", required=True)
    parser.add_argument("--pca-prefix", required=True)
    parser.add_argument("--grm-prefix", required=True)
    parser.add_argument("--admixture-prefix", required=True)
    parser.add_argument("--ld-prune-summary", required=True)
    parser.add_argument("--bfile-extract-summary", required=True)
    parser.add_argument("--pca-summary", required=True)
    parser.add_argument("--grm-summary", required=True)
    parser.add_argument("--admixture-summary", required=True)
    parser.add_argument("--best-k-output", required=True)
    parser.add_argument("--reuse-existing-ld-bfile", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _parse_best_k(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "n/a", "n/a"
    best_k = "n/a"
    cv_error = "n/a"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("K="):
            best_k = stripped.split("=", 1)[1] or "n/a"
        elif stripped.startswith("CV_error="):
            cv_error = stripped.split("=", 1)[1] or "n/a"
    return best_k, cv_error


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    best_k, cv_error = _parse_best_k(Path(args.best_k_output))
    ld_prune_report = _read_text(Path(args.ld_prune_summary)) or "n/a"
    bfile_extract_report = _read_text(Path(args.bfile_extract_summary)) or "n/a"
    pca_report = _read_text(Path(args.pca_summary)) or "n/a"
    grm_report = _read_text(Path(args.grm_summary)) or "n/a"
    admixture_report = _read_text(Path(args.admixture_summary)) or "n/a"
    lines = [
        "Population structure and kinship summary",
        f"Input BFILE: {Path(args.input_bfile)}",
        f"Output dir: {Path(args.output_dir)}",
        f"Reused existing LD-pruned BFILE: {args.reuse_existing_ld_bfile}",
        f"LD-prune prefix: {Path(args.ld_prune_prefix)}",
        f"LD-pruned BFILE prefix: {Path(args.ld_bfile_prefix)}",
        f"PCA prefix: {Path(args.pca_prefix)}",
        f"GRM prefix: {Path(args.grm_prefix)}",
        f"ADMIXTURE dataset prefix: {Path(args.output_dir) / args.admixture_prefix}",
        f"Best K: {best_k}",
        f"CV error: {cv_error}",
        "",
        "LD-prune report:",
        ld_prune_report,
        "",
        "LD-pruned BFILE report:",
        bfile_extract_report,
        "",
        "PCA report:",
        pca_report,
        "",
        "GRM report:",
        grm_report,
        "",
        "ADMIXTURE report:",
        admixture_report,
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
