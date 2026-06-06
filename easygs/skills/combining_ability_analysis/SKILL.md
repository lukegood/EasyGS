---
name: combining_ability_analysis
description: Estimate female GCA, male GCA, and hybrid SCA from a hybrid phenotype CSV using the built-in combining_ability_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Combining Ability Skill

Run combining ability analysis using the built-in `combining_ability_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. read the hybrid phenotype CSV
2. convert hybrid, female, and male identifiers to factors
3. fit a mixed model with female, male, and hybrid as random effects
4. extract female GCA, male GCA, and hybrid SCA effects
5. export the three result CSV files and a compact summary

Do not split this into separate public tools for "female GCA", "male GCA", or "SCA" calculation. Those stay internal inside one complete workflow.

## Tool-First Rule

Use `combining_ability_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the hybrid phenotype CSV
2. treats the hybrid, female, and male columns as factors
3. fits a `sommer::mmer()` mixed model with random effects for female, male, and hybrid
4. extracts female GCA, male GCA, and hybrid SCA values
5. writes `Female_gca.csv`, `Male_gca.csv`, and `sca.csv`
6. writes a compact summary text file

## Required Inputs

- `phenotype_csv`: path to the hybrid phenotype CSV. The default expected columns are `Hybrid`, `Female`, `Male`, and `Phenotype`. Example:

```text
Hybrid,Female,Male,Phenotype
MG_255_X_MG_1538,MG_255,MG_1538,367.2
MG_255_X_MG_1531,MG_255,MG_1531,270.0
MG_255_X_MG_1542,MG_255,MG_1542,288.6
MG_283_X_MG_1538,MG_283,MG_1538,264.8
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `hybrid_column`: hybrid combination column name. Default: `Hybrid`
- `female_column`: female parent column name. Default: `Female`
- `male_column`: male parent column name. Default: `Male`
- `phenotype_column`: phenotype value column name. Default: `Phenotype`

If the user does not override them, defaults remain:


Default outputs:

- `<output_dir>/Female_gca.csv`
- `<output_dir>/Male_gca.csv`
- `<output_dir>/sca.csv`
- `<output_dir>/combining_ability_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_2`
- The pipeline will stop automatically if the required R packages are unavailable:
  `sommer`, `lme4`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `combining_ability_analysis(...)`, collect the required CSV path from the user unless it is already available in the conversation.

Behavior rules:

- When asking for the required input file, always provide a data example with 3 to 4 sample rows together with the format description
- The phenotype input must be `.csv`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output directory
- the three result CSV paths
- the number of female GCA, male GCA, and SCA rows
- the highest female GCA, highest male GCA, and highest SCA effect when inferable
