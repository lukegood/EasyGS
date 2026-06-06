---
name: heritability
description: Calculate single-trait heritability using the built-in heritability_analysis tool and bundled GCTA pipeline from VCF genotype data and phenotype files.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Heritability Calculation Skill

Calculate genetic heritability (h2) using the built-in `heritability_analysis` tool.

This skill provides the workflow and interpretation rules. The actual execution should go through the `heritability_analysis` tool instead of composing raw shell commands by hand. The tool always validates the `EasyGS_2` environment before running.

## Tool-First Rule

Use the `heritability_analysis` tool for execution.

Preferred sequence:

1. Collect or confirm the required paths
2. Call `heritability_analysis(...)`

Only fall back to generic file tools for inspection and confirmation. Do not replace the dedicated tool with ad hoc `exec` commands unless you are debugging the bundled pipeline itself.

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion

## Single-Trait Rule

- Each heritability run uses exactly one trait.
- The user does not need to choose among multiple trait columns.
- The phenotype file should contain one phenotype column only.
- This is a single-trait SNP-based heritability workflow, not a multi-environment mixed model.

## Phenotype File Format

The phenotype file must use this three-column structure:

```text
FID    IID    trait_name
Sample1  Sample1  -1.1535898591114637
Sample2  Sample2  1.198838383708499
Sample3  Sample3  1.3332628547267826
```

Format requirements:

- The header must be exactly three columns: `FID`, `IID`, and one trait column
- Columns must be separated by tab characters
- The third column header is the trait name for this run
- `FID` and `IID` should be sample identifiers
- In most cases here, `FID` and `IID` are the same sample ID
- Do not use phenotype files with multiple trait columns in this skill

## What the Tool Does

The `heritability_analysis` tool wraps the bundled pipeline in `{baseDir}/scripts/heritability.sh` and runs:

1. Environment validation (`EasyGS_2`)
2. Optional VCF sample extraction when `keep` is provided
3. PLINK BED conversion
4. GCTA GRM construction
5. Phenotype reordering to match GRM sample order
6. GCTA REML heritability estimation

The tool also supports:

- `output_dir` as a single root directory
- automatic derivation of `bed/`, `grm/`, and `result/`
- `.vcf` and `.vcf.gz`
- phenotype `.csv` normalization to TSV
- sample-list `.csv` or `.tsv` normalization to plain text
- direct mode from `vcf + pheno` without an explicit sample list
- optional `prefix` for BED/GRM/REML outputs

## Required Inputs

- `vcf`: VCF file containing all candidate samples
- `pheno`: phenotype table in tab-delimited `FID IID trait_name` format with exactly one trait column
- `keep`: optional sample list file
- `prefix`: optional output basename
- output path information:
  - either `output_dir`
  - or all of `bed_dir`, `grm_dir`, and `result_dir`
  - or omit them and let the tool choose its defaults

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the environment check fails
- If the environment check fails, report it clearly and stop
- Do not fall back to hand-written shell commands to bypass this check

## Parameter Collection Rules

Before calling `heritability_analysis(...)`, collect the required paths from the user if they are not already available in the conversation.

Required values to collect:

- VCF file path
- phenotype file path
- output directory or output subdirectories
- optional sample list file path

Behavior rules:

- If the user provides a data directory instead of individual files, inspect that directory and match candidate files by extension before asking follow-up questions.
- When a data directory is provided, use extension-based matching as an initial guess:
  - VCF: prefer `.vcf`, `.vcf.gz`
  - phenotype: prefer `.tsv`, `.txt`, `.csv`
  - sample list: prefer `.txt`, `.tsv`, `.csv`
- After matching candidate files from a directory, present the resolved candidates to the user and ask for confirmation before running the tool.
- When the user provides an input directory, confirmation is mandatory even if only one candidate file is found for each required role.
- Do not silently choose among multiple plausible phenotype or sample-list files.
- If multiple files match the same role, ask the user to confirm which file should be used.
- If no suitable sample-list file is found, it is acceptable to proceed without `keep` and run full-VCF mode directly.
- If the phenotype file does not match the tab-delimited `FID IID trait_name` three-column format, stop and ask the user to fix the file before running.
- If the user provides only one output directory, pass it as `output_dir`.
- If the user already provides separate output directories, pass them as `bed_dir`, `grm_dir`, and `result_dir`.
- If the user does not provide output paths, it is acceptable to let the tool use its defaults.
- If the user does not provide `prefix`, it is acceptable to let the tool derive it automatically.
- Do not invent file paths.
- Confirm the final resolved paths before you execute the run.

## Preferred Tool Calls

Run with one output root:

```text
heritability_analysis(
  vcf="/data/heritability_inputs/1404.vcf.gz",
  pheno="/data/heritability_inputs/pheno.tsv",
  output_dir="/data/heritability_run"
)
```

Run with an explicit sample list:

```text
heritability_analysis(
  vcf="/data/heritability_inputs/1404.vcf.gz",
  pheno="/data/heritability_inputs/pheno.tsv",
  keep="/data/heritability_inputs/sample_ids.txt",
  prefix="herit",
  output_dir="/data/heritability_run"
)
```

Run with explicit output directories:

```text
heritability_analysis(
  vcf="/data/heritability_inputs/1404.vcf.gz",
  pheno="/data/heritability_inputs/pheno.tsv",
  keep="/data/heritability_inputs/sample_ids.txt",
  bed_dir="/data/heritability_run/bed",
  grm_dir="/data/heritability_run/grm",
  result_dir="/data/heritability_run/result"
)
```

## Example Confirmation Message

```text
I found these candidate inputs under /data/heritability_inputs:
- VCF: /data/heritability_inputs/1404.vcf.gz
- Phenotype: /data/heritability_inputs/pheno.tsv
- Sample list: /data/heritability_inputs/sample_ids.txt

The phenotype file appears to follow the required tab-delimited three-column format: FID, IID, and one trait column.

Please confirm whether these are the correct files and whether /data/heritability_run should be used as the output directory.
```

## Result Interpretation

After a successful run, the tool may return a summary like `Estimated h2 (V(G)/Vp): 0.42 (SE 0.08)`.

When explaining results:

- Report the estimated heritability value
- Report the standard error if available
- Point the user to the result prefix and result directory
- Keep the explanation short unless the user asks for deeper statistical interpretation
