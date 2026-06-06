---
name: variance_decomposition_analysis
description: Decompose phenotype variance into genotype, environment, and residual percentages using the built-in variance_decomposition_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Variance Decomposition Skill

Run variance decomposition using the built-in `variance_decomposition_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. read the long-format phenotype CSV
2. standardize the selected columns to genotype, environment, and phenotype roles
3. fit a random-effects mixed model with genotype and environment as random effects
4. extract variance components
5. compute percentage contributions
6. export the result CSV and a compact summary

Do not split this into separate public tools for "fit mixed model" and "percentage calculation". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `variance_decomposition_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the long-format phenotype CSV
2. maps the chosen columns to genotype, environment, and phenotype
3. fits `lme4::lmer(phenotype ~ (1|genotype) + (1|environment), REML = TRUE)`
4. extracts genotype, environment, and residual variance components
5. computes `percent = vcov / total_var * 100`
6. writes `variance_components_percentage.csv`
7. writes a compact summary text file

## Required Inputs

- `phenotype_csv`: path to the long-format phenotype CSV. The default expected columns are `LINE`, `location`, and `PH`. Example:

```text
LINE,location,PH
04K5686_X_Mo17,CQ2012,275.8
04K5686_X_Mo17,DHN2011,254.6
04K5686_X_Mo17,GX2011,235.2
04K5686_X_Mo17,HB2011,232.2
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `genotype_column`: genotype/line column name. Default: `LINE`
- `environment_column`: environment/location column name. Default: `location`
- `phenotype_column`: phenotype value column name. Default: `PH`

If the user does not override them, defaults remain:


Default outputs:

- `<output_dir>/variance_components_percentage.csv`
- `<output_dir>/variance_components_percentage_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_3`

Behavior rules:

- The tool will stop automatically if the `EasyGS_3` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_3`
- The pipeline will stop automatically if the required R packages are unavailable:
  `lme4`, `lmerTest`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `variance_decomposition_analysis(...)`, collect the required CSV path from the user unless it is already available in the conversation.

Behavior rules:

- When asking for the required input file, always provide a data example with 3 to 4 sample rows together with the format description
- The phenotype input must be `.csv`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the result CSV path
- the genotype, environment, and residual variance percentages
- the component with the largest percentage when inferable

