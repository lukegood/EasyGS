---
name: gwas_analysis
description: Run rMVP GWAS from a PLINK BFILE prefix and phenotype CSV using the built-in gwas_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# GWAS Skill

Run GWAS using the built-in `gwas_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the PLINK BFILE prefix and phenotype CSV
2. normalize the phenotype file down to one line-ID column and one trait column
3. convert the BFILE and phenotype into rMVP inputs
4. compute kinship and PCs directly from the MVP genotype data
5. run `rMVP::MVP()` with one or more GWAS models
6. export full-result CSVs, significant-signal CSVs, and plot files
7. write a compact summary

Do not split this into separate public tools for "BFILE conversion", "PC calculation", or "FarmCPU plotting". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `gwas_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the PLINK `BED/BIM/FAM` prefix
2. reads the phenotype CSV and keeps one line column plus one trait column
3. builds rMVP genotype/phenotype files
4. calculates kinship directly from the genotype data
5. calculates principal components
6. runs `rMVP::MVP()` with the requested methods
7. writes method-specific CSVs, signal CSVs, QQ plots, Manhattan plots, PCA, SNP-density, and phenotype-distribution plots
8. writes a compact summary text file

## Required Inputs

- `bfile_prefix`: path prefix for PLINK `BED/BIM/FAM`. Example prefix:

```text
/home/wlg/MyFiles/Project/data/1.GWAS/maize976
```

Example `maize976.fam` rows:

```text
CIMBL32_X_ZHENG58 CIMBL32_X_ZHENG58 0 0 0 -9
CIMBL32_X_MO17 CIMBL32_X_MO17 0 0 0 -9
CIMBL89_X_ZHENG58 CIMBL89_X_ZHENG58 0 0 0 -9
```

Example `maize976.bim` rows:

```text
1 chr1.s_2356 0 2356 C T
1 chr1.s_146037 0 146037 T C
1 chr1.s_203657 0 203657 C T
```

- `phenotype_csv`: phenotype CSV with one line-ID column and one trait column. Example:

```text
LINE,intercept
04K5686_X_MO17,-1.10711819539
04K5686_X_ZHENG58,-11.2907298480106
04K5702_X_MO17,-30.5423512439191
05W002_X_MO17,9.20605204500537
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `line_column`: line-ID column in `phenotype_csv`. Default: first CSV column
- `trait_column`: trait column in `phenotype_csv`. Default: second CSV column
- `methods`: GWAS models to run. Default: `GLM`, `MLM`, `FarmCPU`
- `threshold`: significance threshold passed to rMVP. Default: `0.05`
- `pcs_keep`: PCs computed for rMVP. Default: `5`
- `npc_glm`: number of computed PCs passed into `CV.GLM`. Default: `pcs_keep`
- `npc_mlm`: number of computed PCs passed into `CV.MLM`. Default: `pcs_keep`
- `npc_farmcpu`: number of computed PCs passed into `CV.FarmCPU`. Default: `pcs_keep`
- `ncpus`: CPU count passed to rMVP. Default: `10`

If the user does not override them, defaults remain:


Default output pattern:

- `<output_dir>/<trait>.<method>.csv`
- `<output_dir>/<trait>.<method>_signals.csv`
- `<output_dir>/<trait>.<method>.QQplot.jpg`
- `<output_dir>/<trait>.<method>.Circular-Manhattan.jpg`
- `<output_dir>/<trait>.<method>.Rectangular-Manhattan.jpg`
- `<output_dir>/<trait>.PCA_2D.jpg`
- `<output_dir>/<trait>.Phe_Dist.jpg`
- `<output_dir>/mvp.plink.*`
- `<output_dir>/mvpKin.*`
- `<output_dir>/mvpPC.*`
- `<output_dir>/<trait>_gwas_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R packages are unavailable:
  `rMVP`, `bigmemory`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `gwas_analysis(...)`, collect the required BFILE prefix and phenotype CSV unless they are already available in the conversation.

Behavior rules:

- When asking for the required input files, always provide data examples with 3 to 4 sample rows together with the format description
- The phenotype input must be `.csv`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the trait prefix and methods
- the generated CSV and JPG files
- the number of significant signals per method when inferable
