---
name: qei_detection_analysis
description: Run Fast3VmrMLM multi-environment QEI detection from a PLINK BFILE prefix, a phenotype CSV, and a population-structure CSV using the built-in qei_detection_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# QEI Detection Skill

Run QEI detection using the built-in `qei_detection_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the PLINK BFILE prefix, phenotype CSV, and Q/structure CSV
2. validate that the phenotype and structure files use the required first-column headers
3. run `Fast3VmrMLM_MEJA()` with the chosen trait count and `n_en` vector
4. collect the generated kinship CSV, intermediate CSVs, result Excel files, and optional TIFF plots
5. write a compact summary

Do not split this into separate public tools for kinship construction, trait splitting, or plot generation. Those stay internal inside one complete workflow.

## Tool-First Rule

Use `qei_detection_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. validates the BFILE `BED/BIM/FAM` prefix
2. validates the phenotype CSV and Q/structure CSV headers
3. runs `Fast3VmrMLM::Fast3VmrMLM_MEJA()`
4. writes `<prefix>preKinship.csv`
5. writes `<prefix>trait_i_midresult.csv` and `<prefix>trait_i_result.xlsx`
6. optionally writes TIFF Manhattan plots when `DrawPlot=TRUE`
7. writes a compact summary text file

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
CIMBL89_X_MO17 CIMBL89_X_MO17 0 0 0 -9
```

- `phenotype_csv`: phenotype CSV whose first column must be `<Phenotype>`. Example:

```text
<Phenotype>,trait1_env1,trait1_env2,trait1_env3,trait1_env4
04K5686_X_MO17,275.8,254.6,235.2,232.2
04K5686_X_ZHENG58,222,229.4,218,214.4
04K5702_X_MO17,247.5,245.5,188.75,206.75
05W002_X_MO17,268,278.6,240,238.25
```

- `structure_csv`: population-structure/Q CSV whose first column must be `<Structure>`. Example:

```text
<Structure>,Q1
04K5686_X_MO17,0.051944
04K5686_X_ZHENG58,0.931830
04K5702_X_MO17,0.082082
05W002_X_MO17,0.059069
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `output_prefix`: explicit `fileOut` prefix. Default: `<output_dir>/res`
- `trait_count`: value passed as `trait=`. Default: `1`
- `n_en`: vector passed as `n_en=c(...)`. Default: `[4]` when `trait_count=1`
- `phenotype_id_column`: required first-column header in phenotype CSV. Default: `<Phenotype>`
- `structure_id_column`: required first-column header in structure CSV. Default: `<Structure>`
- `geno_type`: genotype type. Default: `SNP`
- `svrad`: Fast3VmrMLM `svrad`. Default: `20000`
- `svpal`: Fast3VmrMLM `svpal`. Default: `0.01`
- `svmlod`: Fast3VmrMLM `svmlod`. Default: `3`
- `n_threads`: thread count. Default: `10`
- `draw_plot`: whether to request TIFF plots. Default: `false`
- `plot_format`: plot format string. Default: `*.tiff`

If the user does not override them, defaults remain:

- `output_prefix=<output_dir>/res`

Default output pattern:

- `<output_prefix>preKinship.csv`
- `<output_prefix>trait_1_midresult.csv`
- `<output_prefix>trait_1_result.xlsx`
- `<output_prefix.name>_qei_detection_summary.txt` in the same output directory

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_4`

Behavior rules:

- The tool will stop automatically if the `EasyGS_4` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_4`
- The pipeline will stop automatically if the required R package is unavailable:
  `Fast3VmrMLM`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `qei_detection_analysis(...)`, collect the required BFILE prefix, phenotype CSV, and structure CSV unless they are already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- The phenotype input must be `.csv`
- The structure/Q input must be `.csv`
- The BFILE input is a PLINK prefix and must point to existing `.bed`, `.bim`, and `.fam` files
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output prefix
- the generated pre-kinship CSV
- the generated trait-level midresult CSVs and result Excel files
- the count of optional TIFF plot files when `draw_plot=true`
