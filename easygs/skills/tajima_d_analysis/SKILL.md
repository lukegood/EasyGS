---
name: tajima_d_analysis
description: Run vcftools Tajima's D analysis using the built-in tajima_d_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Tajima's D Analysis Skill

Calculate Tajima's D using the built-in `tajima_d_analysis` tool.

This skill is dedicated to the vcftools `--TajimaD` workflow only.

## Tool-First Rule

Use `tajima_d_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled Tajima's D pipeline itself.

## What the Tool Runs

For `.vcf.gz` input:

```text
vcftools --gzvcf <input.vcf.gz> --TajimaD <window_size> --out <prefix>
```

For `.vcf` input:

```text
vcftools --vcf <input.vcf> --TajimaD <window_size> --out <prefix>
```

Example:

```text
vcftools --gzvcf ../../CUBIC/filter.vcf.gz --TajimaD 10000 --out tajima_d
```

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional output controls:

- `window_size`: window size for Tajima's D
- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `window_size=10000`
- `prefix="tajima_d"`

Generated outputs:

- `<prefix>.Tajima.D`
- `<prefix>.log`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `vcftools` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `tajima_d_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user does not mention a window size, it is acceptable to use the default `10000`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `tajima_d`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- total rows
- number of rows with numeric Tajima's D
- mean Tajima's D
- median Tajima's D
- min Tajima's D
- max Tajima's D
- positive, negative, and zero-valued row counts
