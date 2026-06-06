---
name: genotype_imputation_analysis
description: Run Beagle genotype imputation on a VCF/VCF.GZ file using the built-in genotype_imputation_analysis tool and the bundled Beagle jar resource.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Genotype Imputation Skill

Run genotype imputation with the built-in `genotype_imputation_analysis` tool.

This skill is dedicated to Beagle-based imputation only.

## Tool-First Rule

Use `genotype_imputation_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled imputation pipeline itself.

## What the Tool Runs

```text
java -jar <easygs bundled beagle.29Oct24.c8e.jar> gt=<input.vcf|input.vcf.gz> out=<prefix>
```

Example:

```text
java -jar <easygs bundled beagle.29Oct24.c8e.jar> gt=../../CUBIC/filter.vcf.gz out=tianchong
```

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="tianchong"`

Generated outputs:

- `<prefix>.vcf.gz`
- `<prefix>.log`

## Fixed Tooling

This workflow must use the Beagle jar at:

- the bundled `beagle.29Oct24.c8e.jar` resource resolved by EasyGS at runtime

Do not substitute another jar path unless the user explicitly asks to change the implementation.

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `java` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `genotype_imputation_analysis(...)`, collect the required VCF path from the user if it is not already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user provides a directory instead of a single file, inspect it and find likely `.vcf` or `.vcf.gz` candidates before asking a follow-up question
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `tianchong`
- Do not invent file paths

## Preferred Tool Calls

Run with default outputs:

```text
genotype_imputation_analysis(
  vcf="<user_provided_vcf_path>"
)
```

Run with an output directory:

```text
genotype_imputation_analysis(
  vcf="<user_provided_vcf_path>",
  output_dir="<user_provided_output_dir>"
)
```

Run with a custom output prefix:

```text
genotype_imputation_analysis(
  vcf="<user_provided_vcf_path>",
  prefix="<user_provided_prefix>"
)
```
