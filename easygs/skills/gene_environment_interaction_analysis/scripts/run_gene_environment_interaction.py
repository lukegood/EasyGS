#!/usr/bin/env python3
"""Run gene-by-environment interaction ANOVA from VCF and CSV inputs."""

from __future__ import annotations

import argparse
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import allel
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run gene-by-environment interaction analysis.")
    parser.add_argument("--vcf", required=True, help="Input .vcf or .vcf.gz path.")
    parser.add_argument("--phenotype-csv", required=True, help="Input wide phenotype CSV path.")
    parser.add_argument("--env-csv", required=True, help="Input environment-factor mean CSV path.")
    parser.add_argument("--output-dir", required=True, help="Analysis output directory.")
    parser.add_argument("--group-size", required=True, type=int, help="SNPs processed per group.")
    parser.add_argument("--max-workers", type=int, default=None, help="Optional worker count.")
    return parser.parse_args()


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def _load_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    phenotype = pd.read_csv(args.phenotype_csv)
    environment = pd.read_csv(args.env_csv)

    _require_columns(phenotype, ["ID"], "Phenotype CSV")
    if environment.shape[1] < 2:
        raise ValueError("Environment CSV must contain one environment column plus factor columns")

    phenotype["ID"] = phenotype["ID"].astype(str).str.strip()
    env_id_col = environment.columns[0]
    environment[env_id_col] = environment[env_id_col].astype(str).str.strip()

    env_factors = list(environment.columns[1:])
    for factor in env_factors:
        environment[factor] = pd.to_numeric(environment[factor], errors="coerce")

    phenotype_long = pd.melt(phenotype, id_vars=["ID"], var_name="TraitEnv", value_name="Y")
    split_columns = phenotype_long["TraitEnv"].astype(str).str.rsplit("_", n=1, expand=True)
    if split_columns.shape[1] != 2:
        raise ValueError(
            "Phenotype columns must follow '<trait>_<env>' naming, for example PH_JL or PH_BJ"
        )
    phenotype_long["Trait"] = split_columns[0]
    phenotype_long["EnvID"] = split_columns[1]
    phenotype_long["Y"] = pd.to_numeric(phenotype_long["Y"], errors="coerce")
    phenotype_long["EnvID"] = phenotype_long["EnvID"].astype(str).str.strip()
    phenotype_long = phenotype_long.dropna(subset=["Y"]).copy()
    if phenotype_long.empty:
        raise ValueError("No non-missing phenotype values remained after reshaping the phenotype CSV")

    phenotype_env = phenotype_long.merge(
        environment,
        left_on="EnvID",
        right_on=env_id_col,
        how="left",
    )
    if phenotype_env[env_factors].isna().all().all():
        raise ValueError("No phenotype rows matched environment IDs in the environment CSV")
    return phenotype, phenotype_env, env_factors


def _load_genotypes(vcf_path: str, valid_ids: set[str]) -> pd.DataFrame:
    callset = allel.read_vcf(vcf_path, fields=["samples", "calldata/GT"])
    if not callset or "samples" not in callset or "calldata/GT" not in callset:
        raise ValueError(f"Unable to load samples and GT fields from VCF: {vcf_path}")

    vcf_samples = [str(sample) for sample in callset["samples"].tolist()]
    genotype_array = allel.GenotypeArray(callset["calldata/GT"]).to_n_alt().T
    genotype = pd.DataFrame(
        genotype_array,
        columns=[f"SNP{i + 1}" for i in range(genotype_array.shape[1])],
    )
    genotype.insert(0, "ID", vcf_samples)
    genotype["ID"] = genotype["ID"].astype(str).str.strip()
    genotype = genotype[genotype["ID"].isin(valid_ids)].reset_index(drop=True)
    if genotype.empty:
        raise ValueError("No VCF sample IDs matched the phenotype ID column")
    if genotype.shape[1] <= 1:
        raise ValueError("No SNP columns were found after loading the VCF")
    return genotype


def _init_factor_outputs(env_factor_dir: Path, env_factors: list[str]) -> dict[str, Path]:
    env_factor_dir.mkdir(parents=True, exist_ok=True)
    file_map: dict[str, Path] = {}
    for factor in env_factors:
        path = env_factor_dir / f"{factor}_interactions.csv"
        path.write_text("Group,SNP,Factor,FValue,PValue\n", encoding="utf-8")
        file_map[factor] = path
    return file_map


def _process_snp_group(
    group_idx: int,
    group_size: int,
    genotype_df: pd.DataFrame,
    phenotype_env_df: pd.DataFrame,
    env_factors: list[str],
) -> tuple[dict[str, list[str]], list[str]]:
    start = 1 + group_idx * group_size
    end = min(start + group_size, genotype_df.shape[1])
    group_name = f"zu{group_idx + 1}"
    group_snps = genotype_df.iloc[:, [0] + list(range(start, end))].copy()
    merged = phenotype_env_df.merge(group_snps, on="ID", how="inner")

    outputs: dict[str, list[str]] = {}
    errors: list[str] = []
    for factor in env_factors:
        factor_lines: list[str] = []
        for snp in group_snps.columns[1:]:
            try:
                df = merged[[snp, factor, "Y"]].copy()
                df.columns = ["SNP", "Env", "Y"]
                df = df.apply(pd.to_numeric, errors="coerce").dropna()
                if len(df) < 4 or df["SNP"].nunique() < 2 or df["Env"].nunique() < 2:
                    continue

                df["Interaction"] = df["SNP"] * df["Env"]
                if np.isclose(df["Interaction"].std(ddof=0), 0):
                    continue

                model = ols("Y ~ SNP + Env + SNP:Env", data=df).fit()
                anova_table = sm.stats.anova_lm(model, typ=2)
                if "SNP:Env" not in anova_table.index:
                    continue

                fval = anova_table.loc["SNP:Env", "F"]
                pval = anova_table.loc["SNP:Env", "PR(>F)"]
                if pd.isna(fval) or pd.isna(pval):
                    continue
                factor_lines.append(f"{group_name},{snp},{factor},{fval},{pval}\n")
            except Exception as exc:
                errors.append(f"{group_name}-{snp}-{factor}: {exc}")
        if factor_lines:
            outputs[factor] = factor_lines
    return outputs, errors


def main() -> None:
    args = parse_args()
    if args.group_size < 1:
        raise ValueError("group_size must be at least 1")
    if args.max_workers is not None and args.max_workers < 1:
        raise ValueError("max_workers must be at least 1 when provided")

    phenotype, phenotype_env, env_factors = _load_inputs(args)
    genotype = _load_genotypes(args.vcf, set(phenotype["ID"].astype(str)))

    output_dir = Path(args.output_dir)
    env_factor_dir = output_dir / "env_factors"
    file_map = _init_factor_outputs(env_factor_dir, env_factors)

    num_snp_columns = genotype.shape[1] - 1
    num_groups = math.ceil(num_snp_columns / args.group_size)
    if num_groups < 1:
        raise ValueError("No SNP groups were created from the VCF input")

    max_workers = args.max_workers or os.cpu_count() or 1
    max_workers = max(1, min(max_workers, num_groups))

    all_errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _process_snp_group,
                group_idx,
                args.group_size,
                genotype,
                phenotype_env,
                env_factors,
            )
            for group_idx in range(num_groups)
        ]
        for future in as_completed(futures):
            factor_outputs, errors = future.result()
            for factor, lines in factor_outputs.items():
                with file_map[factor].open("a", encoding="utf-8") as handle:
                    handle.writelines(lines)
            all_errors.extend(errors)

    if all_errors:
        error_log_path = output_dir / "interaction_errors.log"
        error_log_path.write_text("\n".join(all_errors) + "\n", encoding="utf-8")

    print("All interaction analyses completed.")
    print("TraitEnv columns processed from phenotype CSV.")
    print(f"SNP groups processed: {num_groups}")
    print(f"Workers used: {max_workers}")
    print(f"Env-factor result dir: {env_factor_dir}")
    if all_errors:
        print(f"Error log: {output_dir / 'interaction_errors.log'}")


if __name__ == "__main__":
    main()
