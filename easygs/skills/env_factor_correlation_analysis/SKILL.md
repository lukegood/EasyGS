---
name: env_factor_correlation_analysis
description: Compute region-specific environmental-factor correlations and render a heatmap with the built-in env_factor_correlation_analysis tool.
metadata: {"easygs":{"emoji":"🌦️","os":["linux"]}}
---

# Environmental-Factor Correlation Analysis Skill

Compute the correlation matrix of environmental factors for one specified region and render a correlation heatmap PDF using the built-in `env_factor_correlation_analysis` tool.

This skill packages the original R workflow into one reusable end-to-end analysis.

## Tool-First Rule

Use `env_factor_correlation_analysis(...)` for execution.

Do not split this into separate user-facing tools for "compute correlation" and "draw heatmap". Those are internal steps inside one complete workflow.

## What the Tool Runs

The bundled pipeline:

1. loads the input `env.csv`
2. filters rows for one region such as `Beijing`
3. selects the environmental-factor columns
4. computes the correlation matrix
5. writes the correlation matrix CSV
6. renders a heatmap PDF
7. builds a small text summary for preview and background-job notifications

## Required Inputs

- `env_csv`: path to the input `env.csv` file. The data should begin with region and date columns, followed by environmental-factor columns, for example:

```text
env_code	Date	DL	GDD	dGDD
Beijing	2014/5/13	14.311	22.347	0
Beijing	2014/5/14	14.344	14.328	8.019
Beijing	2014/5/15	14.376	19.071	4.743
Beijing	2014/5/16	14.407	20.691	1.62
Beijing	2014/5/17	14.439	17.109	3.582
Beijing	2014/5/18	14.469	22.131	5.022
Beijing	2014/5/19	14.499	25.371	3.24
Beijing	2014/5/20	14.528	25.083	0.288
Beijing	2014/5/21	14.557	23.085	1.998
Beijing	2014/5/22	14.585	27.306	4.221
```
- `region`: region name to subset, such as `Beijing`

Optional output controls:

- `output_dir`: directory where outputs should be written
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="<region>_25EF_cor"`

Generated outputs:

- `<prefix>.csv`
- `<prefix>_heatmap.pdf`
- `<prefix>_summary.txt`

Example for `region="Beijing"`:

- `Beijing_25EF_cor.csv`
- `Beijing_25EF_cor_heatmap.pdf`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R package `corrplot` is unavailable
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `env_factor_correlation_analysis(...)`, collect the required CSV path and region from the user unless they are already available in the conversation.

Behavior rules:

- The input file must be a `.csv`
- The file is expected to start with region and date columns, followed by environmental-factor columns
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `<region>_25EF_cor`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the region analyzed
- the number of matched records
- the number of environmental factors included
- the correlation CSV path
- the heatmap PDF path
- the strongest positive and negative factor relationships when inferable
