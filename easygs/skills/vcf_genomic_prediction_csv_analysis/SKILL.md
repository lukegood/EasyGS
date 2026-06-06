---
name: vcf_genomic_prediction_csv_analysis
description: Prepare a 0/1/2 genotype CSV matrix for genomic prediction methods from VCF or VCF.GZ input using the built-in vcf_genomic_prediction_csv_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# VCF Genomic Prediction CSV Analysis Skill

Prepare a genomic-prediction-ready genotype CSV matrix from VCF/VCF.GZ genotype data using the built-in `vcf_genomic_prediction_csv_analysis` tool.

This is not a generic CSV conversion skill. It is dedicated to preparing the sample-by-marker 0/1/2 genotype matrix commonly consumed by genomic prediction workflows, including rrBLUP-style and other genomic selection pipelines. By default, rows are samples and columns are variant IDs.

## Tool-First Rule

Use `vcf_genomic_prediction_csv_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled VCF-to-genomic-prediction-CSV pipeline itself.

## What The Tool Runs

The bundled Python script reads `.vcf` and `.vcf.gz` input, extracts the GT value from each sample genotype field, and encodes biallelic diploid genotypes as additive dosage values:

- `0/0` or `0|0`: `0`
- `0/1`, `1/0`, `0|1`, or `1|0`: `1`
- `1/1` or `1|1`: `2`

Genotype fields with additional FORMAT details are supported, for example `0/1:35,4:39`.

Variant rows with missing genotypes such as `./.` or unsupported genotypes such as `2/2` are skipped and reported in the summary.

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs
- `transpose`: whether to transpose the marker x sample matrix into sample x marker format; defaults to `true`
- `keep_marker_csv`: whether to keep the intermediate marker x sample CSV when transposing; defaults to `false`

If the user does not override them, defaults remain:

- `prefix="genomic_prediction_genotype"`
- `transpose=true`

Generated outputs:

- `<prefix>_final_transposed.csv` when `transpose=true`
- `<prefix>_final.csv` when `transpose=false`
- `<prefix>_marker_matrix.csv` only when `transpose=true` and `keep_marker_csv=true`
- `<prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `python3` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `vcf_genomic_prediction_csv_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user provides a directory instead of a single file, inspect it and find likely `.vcf` or `.vcf.gz` candidates before asking a follow-up question
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `genomic_prediction_genotype`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- input VCF path
- genomic-prediction-ready genotype CSV path
- sample count
- kept variant count
- skipped variants with missing genotypes
- skipped variants with unsupported genotypes
