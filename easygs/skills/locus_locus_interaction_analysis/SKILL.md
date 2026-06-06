---
name: locus_locus_interaction_analysis
description: Run gene-by-gene interaction analysis from a VCF file, a phenotype CSV, and a locus-to-gene mapping file using the built-in locus_locus_interaction_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Gene-by-Gene Interaction Skill

Run gene-by-gene interaction screening using the built-in `locus_locus_interaction_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. load the VCF genotype data
2. load the phenotype CSV with `ID` and `Phenotype`
3. load the locus-to-gene mapping file
4. keep only samples shared by genotype and phenotype
5. keep only loci that are both in the VCF and in the gene map
6. fit `Y ~ SNP1 + SNP2 + SNP1:SNP2` models across locus pairs for every gene pair
7. apply Benjamini-Hochberg FDR correction within each gene pair
8. write significant gene-pair and SNP-pair results plus a compact summary

Do not split this into separate public tools for "VCF loading", "gene-map cleaning", or "pairwise model fitting". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `locus_locus_interaction_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the VCF file with `scikit-allel`
2. converts genotypes to alternate-allele counts (`0/1/2`)
3. reads the phenotype CSV and requires two columns: `ID` and `Phenotype`
4. reads a locus-to-gene mapping file whose first two columns are locus ID and gene name
5. keeps only loci that are present in both the VCF and the gene map
6. runs `Y ~ SNP1 + SNP2 + SNP1:SNP2` across locus pairs for each gene pair
7. applies FDR correction to SNP-pair P values within each gene pair
8. writes:
   `gene_interaction_summary.csv`,
   `significant_snp_pairs_detailed.csv`,
   `analysis_report.txt`,
   and a compact summary text file

## Required Inputs

- `vcf`: path to the genotype file in `.vcf` or `.vcf.gz` format. The VCF must contain variant IDs in the `ID` field. Example:

```text
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	MG_49	MG_50
1	201492	chr1.s_201492	A	G	.	PASS	.	GT	0/0	0/1
1	692383	chr1.s_692383	C	T	.	PASS	.	GT	0/1	0/0
```

- `phenotype_csv`: path to the phenotype CSV with `ID` and `Phenotype` columns. Example:

```text
ID,Phenotype
MG_49,234.6
MG_50,217.2
MG_51,198.5
MG_52,209.8
```

- `gene_map`: path to the locus-to-gene mapping file. The first two columns should be locus ID and gene ID. Tab-separated is preferred. Example:

```text
chr1.s_201492	Zm00001d027240
chr1.s_692383	Zm00001d027259
chr1.s_1022873	Zm00001d027265
chr1.s_1069916	Zm00001d027271
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `prefix`: output folder name. Default: `gene_interaction_results`
- `threshold`: FDR significance threshold. Default: `0.05`

If the user does not override them, defaults remain:

- `prefix="gene_interaction_results"`

Default outputs:

- `<output_dir>/<prefix>/gene_interaction_summary.csv`
- `<output_dir>/<prefix>/significant_snp_pairs_detailed.csv`
- `<output_dir>/<prefix>/analysis_report.txt`
- `<output_dir>/<prefix>/<prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required Python packages are unavailable:
  `pandas`, `numpy`, `statsmodels`, `allel`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `locus_locus_interaction_analysis(...)`, collect the required file paths from the user unless they are already available in the conversation.

Behavior rules:

- When asking for any required input file, always provide a data example together with the format description
- Explain clearly that the phenotype CSV must contain `ID` and `Phenotype`
- Explain clearly that the gene-map file links each locus ID to a gene name
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the summary CSV path
- the detailed SNP-pair CSV path
- the number of significant gene pairs
- the top gene pair when inferable
