---
name: maf_distribution_analysis
description: Run PLINK MAF-distribution analysis with the built-in maf_distribution_analysis tool and bundled reporting scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# MAF Distribution Analysis Skill

Calculate minor allele frequency distribution bins from a PLINK BFILE dataset using the built-in `maf_distribution_analysis` tool.

This skill is dedicated to the PLINK `--freq` workflow on BFILE input only.

## Tool-First Rule

Use `maf_distribution_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled MAF-distribution pipeline itself.

## What the Tool Runs

```text
plink --bfile <input_prefix> --freq --out <prefix>
```

Example:

```text
plink --bfile ~/easyGP/work/1.QC/4.格式转换与预处理/filter --freq --out plink_maf
```

## Required Inputs

- `bfile_prefix`: user-provided PLINK binary prefix with matching `.bed`, `.bim`, and `.fam` files

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="plink_maf"`

Generated outputs:

- `<prefix>.nosex`
- `<prefix>.frq`
- `<prefix>.log`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `plink` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `maf_distribution_analysis(...)`, collect the required BFILE prefix from the user unless it is already available in the conversation.

Behavior rules:

- The BFILE prefix must come from the user or from inspecting a user-provided directory
- If the user provides a directory instead of a single prefix, inspect it and find likely `.bed/.bim/.fam` prefix candidates before asking a follow-up question
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `plink_maf`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- total variant count included in the MAF report
- counts for these bins: `MAF<0.001`, `0.001≤MAF<0.005`, `0.005≤MAF<0.01`, `0.01≤MAF<0.05`, `MAF≥0.05`
- proportion for each MAF bin
