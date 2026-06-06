---
name: env_region_correlation_analysis
description: Compute cross-region correlations from combined environmental-factor profiles and render a heatmap with the built-in env_region_correlation_analysis tool.
metadata: {"easygs":{"emoji":"🌍","os":["linux"]}}
---

# Cross-Region Environmental Correlation Skill

Compute the correlation matrix between regions after combining their environmental-factor profiles from one `env.csv` file, then render a heatmap PDF using the built-in `env_region_correlation_analysis` tool.

This is a separate complete workflow from the region-specific `env_factor_correlation_analysis` tool:

- `env_factor_correlation_analysis` answers "within one region, how do EF columns correlate with each other?"
- `env_region_correlation_analysis` answers "after combining all EF values, how do regions correlate with each other?"

The public workflow is separate because the analysis target changes from factor-to-factor to region-to-region.
Internally, it reuses the same EasyGS workflow pattern, environment validation, and summary/report structure.

## Tool-First Rule

Use `env_region_correlation_analysis(...)` for execution.

Do not split this into separate user-facing tools for "prepare combined matrix", "compute correlation", and "draw heatmap". Those are internal steps inside one complete workflow.

## What the Tool Runs

The bundled pipeline:

1. loads the input `env.csv`
2. groups rows by region
3. flattens each region's environmental-factor matrix into one combined profile
4. computes region-to-region correlations across the combined profiles
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

Optional output controls:

- `output_dir`: directory where outputs should be written
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="各地区原始环境相关性"`

Generated outputs:

- `<prefix>.csv`
- `<prefix>.pdf`
- `<prefix>_summary.txt`

Default example:

- `各地区原始环境相关性.csv`
- `各地区原始环境相关性.pdf`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R package `corrplot` is unavailable
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `env_region_correlation_analysis(...)`, collect the required CSV path from the user unless it is already available in the conversation.

Behavior rules:

- The input file must be a `.csv`
- The file is expected to start with region and date columns, followed by environmental-factor columns
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `各地区原始环境相关性`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the number of regions included
- the number of environmental factors included
- the correlation CSV path
- the heatmap PDF path
- the strongest positive and negative region-to-region relationships when inferable
