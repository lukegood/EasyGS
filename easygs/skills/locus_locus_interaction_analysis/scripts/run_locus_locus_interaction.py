#!/usr/bin/env python3
"""Run gene-by-gene interaction analysis from VCF, phenotype, and gene-map inputs."""

from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path

import allel
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


SUMMARY_COLUMNS = [
    "Gene1",
    "Gene2",
    "Num_Significant_Pairs",
    "Avg_F_value",
    "Avg_P_value",
    "Avg_FDR",
    "Avg_R_squared",
]

DETAIL_COLUMNS = [
    "Gene1",
    "Gene2",
    "SNP1",
    "SNP2",
    "F_value",
    "P_value",
    "FDR",
    "R_squared",
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gene-by-gene interaction analysis tool.")
    parser.add_argument("--vcf", required=True, help="Input VCF or VCF.GZ path.")
    parser.add_argument("--phenotype-csv", required=True, help="Input phenotype CSV path.")
    parser.add_argument("--gene-map", required=True, help="Input locus-to-gene mapping file path.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--threshold", type=float, default=0.05, help="FDR threshold.")
    return parser.parse_args()


def validate_files(args: argparse.Namespace) -> None:
    required_files = {
        "VCF": args.vcf,
        "Phenotype CSV": args.phenotype_csv,
        "Gene map": args.gene_map,
    }
    missing = [f"{label}: {path}" for label, path in required_files.items() if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required input files:\n" + "\n".join(missing))


def setup_output_directory(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def read_phenotype(phe_file: str) -> pd.DataFrame:
    phenotype = pd.read_csv(phe_file)
    required_columns = ["ID", "Phenotype"]
    missing_columns = [column for column in required_columns if column not in phenotype.columns]
    if missing_columns:
        raise ValueError(
            "Phenotype CSV must contain ID and Phenotype columns; "
            f"missing columns: {', '.join(missing_columns)}"
        )

    phenotype = phenotype[["ID", "Phenotype"]].copy()
    phenotype["ID"] = phenotype["ID"].astype(str).str.strip()
    phenotype["Phenotype"] = pd.to_numeric(phenotype["Phenotype"], errors="coerce")
    phenotype = phenotype.dropna(subset=["ID", "Phenotype"]).reset_index(drop=True)
    if phenotype.empty:
        raise ValueError("No valid phenotype rows remained after filtering missing ID/Phenotype values")
    return phenotype


def _read_mapping_with_separator(gene_map_file: str, separator: str) -> pd.DataFrame | None:
    try:
        frame = pd.read_csv(
            gene_map_file,
            sep=separator,
            header=None,
            names=["Locus", "Gene"],
            usecols=[0, 1],
            dtype=str,
            engine="python",
        )
    except Exception:
        return None
    if "Gene" not in frame.columns or frame["Gene"].isna().all():
        return None
    return frame


def read_gene_mapping(gene_map_file: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    mapping_frame = None
    for separator in ("\t", ",", r"\s+"):
        mapping_frame = _read_mapping_with_separator(gene_map_file, separator)
        if mapping_frame is not None:
            break

    if mapping_frame is None:
        fallback = pd.read_csv(gene_map_file, header=None, dtype=str, engine="python")
        if fallback.shape[1] < 2:
            raise ValueError("Gene mapping file must contain at least two columns")
        mapping_frame = fallback.iloc[:, :2].copy()
        mapping_frame.columns = ["Locus", "Gene"]

    mapping_frame["Locus"] = mapping_frame["Locus"].astype(str).str.strip()
    mapping_frame["Gene"] = mapping_frame["Gene"].astype(str).str.strip()
    mapping_frame = mapping_frame.replace({"": np.nan}).dropna(subset=["Locus", "Gene"]).reset_index(drop=True)
    if mapping_frame.empty:
        raise ValueError("No usable locus-to-gene mappings were found in the gene map file")

    locus_to_gene = dict(zip(mapping_frame["Locus"], mapping_frame["Gene"]))
    gene_to_loci = mapping_frame.groupby("Gene", sort=True)["Locus"].apply(list).to_dict()
    return locus_to_gene, gene_to_loci


def read_genotype(vcf_file: str, valid_ids: set[str]) -> pd.DataFrame:
    callset = allel.read_vcf(vcf_file, fields=["samples", "variants/ID", "calldata/GT"])
    if not callset:
        raise ValueError(f"Unable to read VCF fields from: {vcf_file}")

    required_fields = {"samples", "variants/ID", "calldata/GT"}
    missing_fields = sorted(required_fields.difference(callset.keys()))
    if missing_fields:
        raise ValueError(f"VCF is missing required fields: {', '.join(missing_fields)}")

    samples = [str(sample).strip() for sample in callset["samples"].tolist()]
    loci = [str(locus).strip() for locus in callset["variants/ID"].tolist()]
    genotype_array = allel.GenotypeArray(callset["calldata/GT"]).to_n_alt().T

    genotype = pd.DataFrame(genotype_array, columns=loci)
    genotype.insert(0, "ID", samples)
    genotype = genotype[genotype["ID"].isin(valid_ids)].reset_index(drop=True)
    if genotype.empty:
        raise ValueError("No VCF sample IDs matched the phenotype ID column")
    if genotype.shape[1] <= 1:
        raise ValueError("No variant IDs were loaded from the VCF")
    return genotype


def analyze_interaction(
    snp1: str,
    snp2: str,
    genotype_df: pd.DataFrame,
    phenotype_df: pd.DataFrame,
) -> tuple[str, str, float, float, float] | None:
    try:
        merged = phenotype_df[["ID", "Phenotype"]].merge(
            genotype_df[["ID", snp1, snp2]],
            on="ID",
            how="inner",
        ).dropna()
        if merged.empty:
            return None

        merged.columns = ["ID", "Y", "SNP1", "SNP2"]
        if merged["SNP1"].nunique() < 2 or merged["SNP2"].nunique() < 2:
            return None

        model = smf.ols("Y ~ SNP1 + SNP2 + SNP1:SNP2", data=merged).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        if "SNP1:SNP2" not in anova_table.index:
            return None

        f_value = anova_table.loc["SNP1:SNP2", "F"]
        p_value = anova_table.loc["SNP1:SNP2", "PR(>F)"]
        if pd.isna(f_value) or pd.isna(p_value):
            return None
        return (snp1, snp2, float(f_value), float(p_value), float(model.rsquared))
    except Exception:
        return None


def analyze_gene_pair(
    gene1: str,
    gene2: str,
    gene_to_loci: dict[str, list[str]],
    genotype: pd.DataFrame,
    phenotype: pd.DataFrame,
    threshold: float,
) -> dict[str, object] | None:
    loci1 = gene_to_loci[gene1]
    loci2 = gene_to_loci[gene2]

    results: list[tuple[str, str, float, float, float]] = []
    for snp1, snp2 in product(loci1, loci2):
        interaction = analyze_interaction(snp1, snp2, genotype, phenotype)
        if interaction is not None:
            results.append(interaction)

    if not results:
        return None

    p_values = [result[3] for result in results]
    _, fdr_values, _, _ = multipletests(p_values, method="fdr_bh")

    significant_pairs: list[dict[str, float | str]] = []
    for result, fdr in zip(results, fdr_values):
        snp1, snp2, f_value, p_value, r_squared = result
        if float(fdr) < threshold:
            significant_pairs.append(
                {
                    "SNP1": snp1,
                    "SNP2": snp2,
                    "F_value": f_value,
                    "P_value": p_value,
                    "FDR": float(fdr),
                    "R_squared": r_squared,
                }
            )

    if not significant_pairs:
        return None

    avg_f = float(np.mean([pair["F_value"] for pair in significant_pairs]))
    avg_p = float(np.mean([pair["P_value"] for pair in significant_pairs]))
    avg_fdr = float(np.mean([pair["FDR"] for pair in significant_pairs]))
    avg_rsq = float(np.mean([pair["R_squared"] for pair in significant_pairs]))

    return {
        "Gene1": gene1,
        "Gene2": gene2,
        "Num_Significant_Pairs": len(significant_pairs),
        "Avg_F_value": avg_f,
        "Avg_P_value": avg_p,
        "Avg_FDR": avg_fdr,
        "Avg_R_squared": avg_rsq,
        "Significant_Pairs": significant_pairs,
    }


def main_analysis(args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if args.threshold <= 0:
        raise ValueError("threshold must be greater than 0")

    validate_files(args)
    output_dir = setup_output_directory(Path(args.output_dir))

    phenotype = read_phenotype(args.phenotype_csv)
    _, gene_to_loci = read_gene_mapping(args.gene_map)
    genotype = read_genotype(args.vcf, set(phenotype["ID"]))

    available_loci = set(genotype.columns) - {"ID"}
    original_gene_count = len(gene_to_loci)
    filtered_gene_to_loci: dict[str, list[str]] = {}
    for gene, loci in gene_to_loci.items():
        usable_loci = [locus for locus in loci if locus in available_loci]
        if usable_loci:
            filtered_gene_to_loci[gene] = usable_loci

    gene_to_loci = filtered_gene_to_loci
    gene_list = sorted(gene_to_loci.keys())
    dropped_gene_count = original_gene_count - len(gene_list)
    if len(gene_list) < 2:
        raise ValueError("Fewer than two genes have usable loci in the VCF")

    all_results: list[dict[str, object]] = []
    detailed_results: list[dict[str, object]] = []
    total_pairs = len(gene_list) * (len(gene_list) - 1) // 2

    for i, gene1 in enumerate(gene_list):
        for gene2 in gene_list[i + 1 :]:
            result = analyze_gene_pair(gene1, gene2, gene_to_loci, genotype, phenotype, args.threshold)
            if result is None:
                continue

            all_results.append(
                {
                    "Gene1": result["Gene1"],
                    "Gene2": result["Gene2"],
                    "Num_Significant_Pairs": result["Num_Significant_Pairs"],
                    "Avg_F_value": result["Avg_F_value"],
                    "Avg_P_value": result["Avg_P_value"],
                    "Avg_FDR": result["Avg_FDR"],
                    "Avg_R_squared": result["Avg_R_squared"],
                }
            )
            for pair in result["Significant_Pairs"]:
                detailed_results.append(
                    {
                        "Gene1": result["Gene1"],
                        "Gene2": result["Gene2"],
                        "SNP1": pair["SNP1"],
                        "SNP2": pair["SNP2"],
                        "F_value": pair["F_value"],
                        "P_value": pair["P_value"],
                        "FDR": pair["FDR"],
                        "R_squared": pair["R_squared"],
                    }
                )

    summary_df = pd.DataFrame(all_results, columns=SUMMARY_COLUMNS)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(["Avg_FDR", "Avg_P_value", "Gene1", "Gene2"]).reset_index(drop=True)
    detail_df = pd.DataFrame(detailed_results, columns=DETAIL_COLUMNS)
    if not detail_df.empty:
        detail_df = detail_df.sort_values(["FDR", "P_value", "Gene1", "Gene2", "SNP1", "SNP2"]).reset_index(drop=True)

    summary_file = output_dir / "gene_interaction_summary.csv"
    detail_file = output_dir / "significant_snp_pairs_detailed.csv"
    summary_df.to_csv(summary_file, index=False)
    detail_df.to_csv(detail_file, index=False)

    report_file = output_dir / "analysis_report.txt"
    with report_file.open("w", encoding="utf-8") as handle:
        handle.write("Gene-by-gene interaction analysis report\n")
        handle.write("=" * 50 + "\n")
        handle.write(f"Analysis time: {pd.Timestamp.now()}\n")
        handle.write(f"VCF file: {args.vcf}\n")
        handle.write(f"Phenotype file: {args.phenotype_csv}\n")
        handle.write(f"Gene map file: {args.gene_map}\n")
        handle.write(f"Output directory: {args.output_dir}\n")
        handle.write(f"Threshold: {args.threshold}\n")
        handle.write("\nData statistics:\n")
        handle.write(f"Phenotype samples: {len(phenotype)}\n")
        handle.write(f"Original genes: {original_gene_count}\n")
        handle.write(f"Usable genes: {len(gene_list)}\n")
        handle.write(f"Dropped genes: {dropped_gene_count}\n")
        handle.write(f"Usable loci in VCF: {len(available_loci)}\n")
        handle.write(f"Gene pairs tested: {total_pairs}\n")
        handle.write(f"Significant gene pairs: {len(summary_df)}\n")
        handle.write(f"Significant SNP pairs: {len(detail_df)}\n")

    print("Gene-by-gene interaction analysis completed.")
    print(f"Phenotype samples used: {len(phenotype)}")
    print(f"Usable genes: {len(gene_list)}")
    print(f"Gene pairs tested: {total_pairs}")
    print(f"Significant gene pairs: {len(summary_df)}")
    print(f"Detailed SNP-pair rows: {len(detail_df)}")
    print(f"Summary CSV: {summary_file}")
    print(f"Detailed CSV: {detail_file}")
    print(f"Analysis report: {report_file}")

    return all_results, detailed_results


if __name__ == "__main__":
    arguments = parse_arguments()
    try:
        main_analysis(arguments)
    except KeyboardInterrupt:
        print("Analysis interrupted by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        sys.exit(1)
