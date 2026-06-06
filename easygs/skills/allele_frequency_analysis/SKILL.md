---
name: allele_frequency_analysis
description: Run vcftools allele-frequency analysis and summarize polymorphic-site proportion using the built-in allele_frequency_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Allele Frequency Analysis Skill

Calculate allele-frequency output and summarize the polymorphic-site proportion using the built-in `allele_frequency_analysis` tool.

This skill is dedicated to the vcftools `--freq` workflow only.

## Tool-First Rule

Use `allele_frequency_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled allele-frequency pipeline itself.

## What the Tool Runs

For `.vcf.gz` input:

```text
vcftools --gzvcf <input.vcf.gz> --freq --out <prefix>
```

For `.vcf` input:

```text
vcftools --vcf <input.vcf> --freq --out <prefix>
```

Example:

```text
vcftools --gzvcf ../../CUBIC/filter.vcf.gz --freq --out allele_freq
```

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="allele_freq"`

Generated outputs:

- `<prefix>.frq`
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

Before calling `allele_frequency_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user provides a directory instead of a single file, inspect it and find likely `.vcf` or `.vcf.gz` candidates before asking a follow-up question
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `allele_freq`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- total site count
- polymorphic site count
- polymorphic site proportion
- mean minor allele frequency for polymorphic sites
