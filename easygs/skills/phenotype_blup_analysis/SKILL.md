---
name: phenotype_blup_analysis
description: Compute BLUP values from a multi-environment phenotype CSV using the built-in phenotype_blup_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Phenotype BLUP Skill

Run multi-environment phenotype BLUP estimation using the built-in `phenotype_blup_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. read the phenotype CSV in wide format
2. reshape region columns into a long table
3. fit the mixed model `Phenotype ~ (1|LINE_ID) + Environment`
4. extract line-level random effects as BLUP values
5. export the BLUP CSV and a compact summary

Do not split this into separate public tools for "wide-to-long conversion", "mixed-model fitting", or "BLUP extraction". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `phenotype_blup_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the multi-environment phenotype CSV
2. keeps the first column as `LINE_ID`
3. melts the environment columns into `Environment` and phenotype values
4. fits `PlantHeight ~ (1|LINE_ID) + Environment` using `lmer`
5. extracts BLUP values from `ranef(model)$LINE_ID`
6. writes the BLUP CSV
7. writes a compact summary text file

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
- `prefix`: basename for outputs. Default is derived from the input file name, for example `9地区株高.csv` -> `9地区下株高BLUP值`

If the user does not override them, defaults remain:


Default outputs:

- `<output_dir>/<prefix>.csv`
- `<output_dir>/<prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R packages are unavailable:
  `lme4`, `reshape2`, `dplyr`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `phenotype_blup_analysis(...)`, collect the required CSV path from the user unless it is already available in the conversation.

Behavior rules:

- When asking for the required input file, always provide a data example with 3 to 4 sample rows together with the format description
- The phenotype input must be `.csv`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the BLUP CSV path
- the number of lines with BLUP estimates
- the highest BLUP sample when inferable
