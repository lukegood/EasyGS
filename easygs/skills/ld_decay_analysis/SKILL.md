---
name: ld_decay_analysis
description: Run PopLDdecay LD decay analysis with the built-in ld_decay_analysis tool and bundled reporting scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# LD Decay Analysis Skill

Calculate linkage disequilibrium decay statistics from a VCF/VCF.GZ dataset using the built-in `ld_decay_analysis` tool.

This skill is dedicated to the PopLDdecay `-InVCF/-OutStat` workflow only.

## Tool-First Rule

Use `ld_decay_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled LD-decay pipeline itself.

## What the Tool Runs

```text
PopLDdecay -InVCF <input.vcf.gz> -OutStat <prefix>
```

Example:

```text
PopLDdecay -InVCF ~/easyGP/work/CUBIC/filter.vcf.gz -OutStat LDdecay
```

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="LDdecay"`

Generated outputs:

- `<prefix>.stat.gz`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `PopLDdecay` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `ld_decay_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user provides a directory instead of a single file, inspect it and find likely `.vcf` or `.vcf.gz` candidates before asking a follow-up question
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `LDdecay`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- total LD-decay statistic points in the `.stat.gz` report
- parsed distance range when available
- mean and maximum LD value when an R²-like column is available
- the earliest distance where the mean LD falls below common thresholds when inferable
