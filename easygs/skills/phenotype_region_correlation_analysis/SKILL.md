---
name: phenotype_region_correlation_analysis
description: Compute cross-region phenotype correlations from a phe.csv file and render a heatmap with the built-in phenotype_region_correlation_analysis tool.
metadata: {"easygs":{"emoji":"📈","os":["linux"]}}
---

# Cross-Region Phenotype Correlation Skill

Compute the correlation matrix between phenotype columns from one `phe.csv` file, then render a heatmap PDF using the built-in `phenotype_region_correlation_analysis` tool.

This is a separate complete workflow from `env_region_correlation_analysis`:

- `env_region_correlation_analysis` answers "after combining all environmental-factor values, how do regions correlate with each other?"
- `phenotype_region_correlation_analysis` answers "across regional phenotype columns in `phe.csv`, how do those region-level phenotypes correlate with each other?"

The public workflow is separate because the input structure and biological meaning change from environmental factors to phenotype values.
Internally, it reuses the same EasyGS workflow pattern, environment validation, and summary/report structure.

## Tool-First Rule

Use `phenotype_region_correlation_analysis(...)` for execution.

Do not split this into separate user-facing tools for "extract phenotype columns", "compute correlation", and "draw heatmap". Those are internal steps inside one complete workflow.

## What the Tool Runs

The bundled pipeline:

1. loads the input `phe.csv`
2. keeps the sample ID column plus all regional phenotype columns
3. computes the region-to-region phenotype correlation matrix
4. writes the correlation matrix CSV
5. renders a heatmap PDF
6. builds a small text summary for preview and background-job notifications

## Required Inputs

- `phe_csv`: path to the input `phe.csv` file. The data should begin with one sample/material ID column, followed by phenotype columns for each region, for example:

```text
ID,PH_JL,PH_LN,PH_BJ,PH_HB,PH_HN
MG_49,234.6,241.13,249.6,228.8,215.25
MG_50,217.2,204,212.2,196.75,173.6
MG_51,198.5,207.4,202.75,233.33,166.2
MG_52,209.8,230.5,209.8,189.4,184.5
MG_53,219.2,200,224.25,183.75,182.25
```

Optional output controls:

- `output_dir`: directory where outputs should be written
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="各地区表型相关性"`

Generated outputs:

- `<prefix>.csv`
- `<prefix>.pdf`
- `<prefix>_summary.txt`

Default example:

- `各地区表型相关性.csv`
- `各地区表型相关性.pdf`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R package `corrplot` is unavailable
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `phenotype_region_correlation_analysis(...)`, collect the required CSV path from the user unless it is already available in the conversation.

Behavior rules:

- The input file must be a `.csv`
- The file is expected to start with one sample/material ID column, followed by regional phenotype columns
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `各地区表型相关性`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the number of samples included
- the number of regional phenotype columns included
- the correlation CSV path
- the heatmap PDF path
- the strongest positive and negative phenotype-column relationships when inferable
