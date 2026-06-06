---
name: reaction_norm_analysis
description: Convert a multi-environment phenotype CSV to long format and compute reaction norm intercept/slope values using the built-in reaction_norm_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Reaction Norm Skill

Run reaction norm analysis using the built-in `reaction_norm_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. read the phenotype CSV in wide format
2. reshape all environment columns into a long phenotype table
3. export the long-format helper CSV
4. fit a Finlay-Wilkinson-style reaction norm model
5. extract intercept and slope values for each line
6. export the intercept/slope CSV and a compact summary

Do not split this into separate public tools for "wide-to-long conversion", "FW fitting", or "slope extraction". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `reaction_norm_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the multi-environment phenotype CSV
2. keeps the first column as line ID
3. reshapes all remaining environment columns into `location` and phenotype value columns
4. writes `用于计算斜率截距的表型文件.csv`
5. computes an environment mean index and fits per-line regressions on that index
6. extracts `intercept` and `slope` values for each line
7. writes `PH_intercep_slope_values.csv`
8. writes a compact summary text file

## Required Inputs

- `phenotype_csv`: path to the multi-environment phenotype CSV in wide format. The first column must be `LINE_ID`, followed by one column per environment. Example:

```text
LINE_ID,CQ2012,DHN2011,GX2011,HB2011,HB2012,HN2012,SC2011,YN2011,YN2012
04K5686_X_Mo17,275.8,254.6,235.2,232.2,264.6,288.4,240.25,242,213
04K5686_X_Zheng58,222,229.4,218,214.4,224.63,241.2,216.25,201.33,194.5
04K5702_X_Mo17,247.5,245.5,188.75,206.75,257.3,297.75,207,215,211.2
05W002_X_Mo17,268,278.6,240,238.25,263.8,290.5,246,271.67,240.4
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `trait_label`: trait label used in the long-format value column and in the intercept/slope filename prefix. Default: `PH`

If the user does not override them, defaults remain:

- `trait_label="PH"`

Default outputs:

- `<output_dir>/用于计算斜率截距的表型文件.csv`
- `<output_dir>/PH_intercep_slope_values.csv`
- `<output_dir>/PH_intercep_slope_values_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R packages are unavailable:
  `tidyr`, `dplyr`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `reaction_norm_analysis(...)`, collect the required CSV path from the user unless it is already available in the conversation.

Behavior rules:

- When asking for the required input file, always provide a data example with 3 to 4 sample rows together with the format description
- The phenotype input must be `.csv`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the long-format helper CSV path
- the intercept/slope CSV path
- the number of lines with intercept/slope estimates
- the highest slope line when inferable
