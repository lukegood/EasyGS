#!/usr/bin/env python3
"""Summarize GEBV outputs and materialize derived ranking tables."""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize GCTA GEBV outputs.")
    parser.add_argument("--grm-prefix", required=True, help="Input GRM prefix.")
    parser.add_argument("--pheno", required=True, help="Input phenotype file.")
    parser.add_argument("--hsq", required=True, help="GCTA .hsq output path.")
    parser.add_argument("--blp", required=True, help="GCTA .indi.blp output path.")
    parser.add_argument("--log", required=True, help="GCTA .log output path.")
    parser.add_argument("--clean-output", required=True, help="Output path for cleaned GEBV table.")
    parser.add_argument("--top-output", required=True, help="Output path for selected top individuals.")
    parser.add_argument("--summary-output", required=True, help="Output path for summary text.")
    parser.add_argument("--top-percent", required=True, type=int, help="Top percentage to retain.")
    return parser.parse_args()


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _parse_hsq(path: Path) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[0] == "V(G)/Vp":
            return f"{parts[1]} (SE {parts[2]})"
    return ""


def _load_blp_rows(path: Path) -> list[tuple[str, str, str, float]]:
    rows: list[tuple[str, str, str, float]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        gebv_value = _parse_float(parts[3])
        if gebv_value is None:
            if line_number == 1:
                continue
            raise ValueError(f"Unable to parse GEBV value from line {line_number} in {path}")
        rows.append((parts[0], parts[1], parts[3], gebv_value))
    if not rows:
        raise ValueError(f"No usable GEBV rows were found in {path}")
    return rows


def _selection_count(total: int, top_percent: int) -> int:
    if total <= 0:
        return 0
    count = (total * top_percent) // 100
    return min(total, max(1, count))


def _write_clean_output(path: Path, rows: list[tuple[str, str, str, float]]) -> None:
    lines = ["FID IID GEBV"]
    lines.extend(f"{fid} {iid} {gebv_raw}" for fid, iid, gebv_raw, _ in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_top_output(path: Path, rows: list[tuple[str, str, str, float]]) -> None:
    lines = [f"{fid} {iid} {gebv_raw}" for fid, iid, gebv_raw, _ in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.top_percent < 1 or args.top_percent > 100:
        raise ValueError("top_percent must be between 1 and 100")

    hsq_path = Path(args.hsq)
    blp_path = Path(args.blp)
    clean_output = Path(args.clean_output)
    top_output = Path(args.top_output)
    summary_output = Path(args.summary_output)

    for path in (clean_output, top_output, summary_output):
        path.parent.mkdir(parents=True, exist_ok=True)

    h2_summary = _parse_hsq(hsq_path)
    rows = _load_blp_rows(blp_path)
    _write_clean_output(clean_output, rows)

    ranked_rows = sorted(rows, key=lambda item: item[3], reverse=True)
    select_count = _selection_count(len(ranked_rows), args.top_percent)
    selected_rows = ranked_rows[:select_count]
    _write_top_output(top_output, selected_rows)

    gebv_values = [row[3] for row in ranked_rows]
    top_preview = [f"{fid} {iid} {gebv_raw}" for fid, iid, gebv_raw, _ in selected_rows[:5]]

    lines = [
        "=== GEBV育种值分析 ===",
        f"输入GRM前缀: {Path(args.grm_prefix)}",
        f"输入表型文件: {Path(args.pheno)}",
        f"GCTA hsq文件: {hsq_path}",
        f"GCTA BLP文件: {blp_path}",
        f"GCTA日志文件: {Path(args.log)}",
        f"育种值文件: {clean_output}",
        f"最优个体文件（前{args.top_percent}%）: {top_output}",
        f"总个体数: {len(ranked_rows)}",
        f"入选个体数: {select_count}",
        f"平均GEBV: {statistics.mean(gebv_values):.6f}",
        f"最高GEBV: {ranked_rows[0][0]} {ranked_rows[0][1]} {ranked_rows[0][2]}",
        f"最低GEBV: {ranked_rows[-1][0]} {ranked_rows[-1][1]} {ranked_rows[-1][2]}",
    ]
    if h2_summary:
        lines.append(f"估计遗传力 V(G)/Vp: {h2_summary}")
    if top_preview:
        lines.append("前5个最优个体:")
        lines.extend(top_preview)

    summary_output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
