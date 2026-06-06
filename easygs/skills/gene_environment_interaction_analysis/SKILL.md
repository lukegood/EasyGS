---
name: gene_environment_interaction_analysis
description: Run SNP-by-environment-factor interaction ANOVA from a VCF, a phenotype CSV, and an environment-factor mean CSV using the built-in gene_environment_interaction_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Gene-by-Environment Interaction Skill

Run SNP-by-environment-factor interaction analysis using the built-in `gene_environment_interaction_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. read genotypes from a VCF file
2. reshape wide phenotype columns such as `PH_JL`, `PH_LN`, `PH_BJ`
3. merge regional environment-factor means
4. fit `Y ~ SNP + Env + SNP:Env` ANOVA models
5. export one interaction result file per environmental factor
6. build a text summary for preview and background-job notifications

Do not split this into separate public tools for "VCF decoding", "phenotype reshaping", or "single-factor interaction testing". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `gene_environment_interaction_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. loads the input VCF/VCF.GZ and converts genotypes to alternate-allele counts
2. loads the wide phenotype CSV and reshapes all `Trait_Env` columns
3. loads the region-level environment-factor mean CSV
4. joins phenotype, genotype, and environment tables by ID and environment code
5. runs `Y ~ SNP + Env + SNP:Env` ANOVA for every SNP and environmental factor
6. writes per-factor CSV files under `env_factors/`
7. writes a compact summary text file

## Required Inputs

- `vcf`: path to the input `.vcf` or `.vcf.gz` file. Sample IDs in the VCF must match the phenotype `ID` column, for example:

```text
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	MG_1000	MG_1001	MG_1002
1	1067986	chr1.s_1067986	A	A	.	PASS	.	GT	0/0	0/0	0/0
1	1068121	chr1.s_1068121	A	A	.	PASS	.	GT	0/0	0/0	0/0
```

- `phenotype_csv`: path to the phenotype CSV in wide format. The first column must be `ID`, and regional trait columns should follow `<trait>_<env>` naming, for example:

```text
ID,PH_JL,PH_LN,PH_BJ,PH_HB,PH_HN
MG_49,234.6,241.13,249.6,228.8,215.25
MG_50,217.2,204,212.2,196.75,173.6
MG_51,198.5,207.4,202.75,233.33,166.2
MG_52,209.8,230.5,209.8,189.4,184.5
MG_53,219.2,200,224.25,183.75,182.25
```

- `env_csv`: path to the region-level environment-factor mean CSV. The first column stores environment IDs such as `BJ`, `HB`, `HN`, `JL`, `LN`, followed by environmental factor columns, for example:

```text
env,DL,GDD,dGDD,DTR,PTT
BJ,13.9308666666667,24.57782,2.75673333333333,23.15124,348.419468666667
HB,13.1262133333333,24.3513666666667,2.51986,22.6752,333.167522666667
HN,12.9729866666667,25.2959933333333,2.52274666666667,20.48088,340.244692666667
JL,14.3564933333333,17.60544,2.36148,21.62916,257.755178
LN,14.0801933333333,21.50472,2.55774,22.95036,307.263327333333
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `prefix`: output folder name. Default: `gene_env_huzuo_ANOVA`
- `group_size`: SNPs processed per group. Default: `1`
- `max_workers`: optional worker count for parallel processing

If the user does not override them, defaults remain:

- `prefix="gene_env_huzuo_ANOVA"`

Default outputs:

- `<output_dir>/<prefix>/env_factors/*.csv`
- `<output_dir>/<prefix>/<prefix>_summary.txt`

Example default result layout:

```text
gene_env_huzuo_ANOVA/
├── gene_env_huzuo_ANOVA_summary.txt
└── env_factors/
    ├── APAR_interactions.csv
    ├── CPAR_interactions.csv
    ├── DL_interactions.csv
    └── ...
```

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required Python packages are unavailable:
  `numpy`, `pandas`, `statsmodels`, `allel`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `gene_environment_interaction_analysis(...)`, collect the required file paths from the user unless they are already available in the conversation.

Behavior rules:

- When asking for any required input file, always provide a data example together with the format description
- The genotype input must be `.vcf` or `.vcf.gz`
- The phenotype input must be `.csv` and must start with the `ID` column
- The environment-factor input must be `.csv` and must use its first column as the environment identifier
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the per-factor result directory
- the number of factor files generated
- the number of non-empty interaction files
- the total number of interaction rows
- the most significant interaction when inferable
