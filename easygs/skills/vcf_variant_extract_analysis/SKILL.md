---
name: vcf_variant_extract_analysis
description: Extract a subset VCF from a VCF/VCF.GZ file by variant ID list using the built-in vcf_variant_extract_analysis tool and bundled bcftools workflow.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# VCF Variant Extract Skill

Extract a subset VCF from a VCF or VCF.GZ file by variant ID list using the built-in `vcf_variant_extract_analysis` tool.

This should be treated as one complete workflow rather than an ad hoc shell command, because the analysis depends on one tightly coupled chain:

1. validate the input VCF/VCF.GZ
2. normalize the variant ID list into one-ID-per-line format
3. run `bcftools view -i 'ID=@file'`
4. write the extracted VCF
5. build a compact summary for preview and job notifications

## Tool-First Rule

Use `vcf_variant_extract_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. loads the input VCF/VCF.GZ file
2. normalizes a user-provided variant ID list
3. runs `bcftools view -i 'ID=@<variant_ids.txt>'`
4. writes an extracted `.vcf`
5. writes a compact summary text file

## Required Inputs

- `vcf`: path to the input `.vcf` or `.vcf.gz` file
- `variant_ids`: variant ID list as a file path or inline text

The variant ID list should contain one variant ID per line. Example:

```text
chr1.s_1067986
chr1.s_1068121
chr1.s_1068288
chr1.s_1068648
chr1.s_1068668
chr1.s_1069042
chr1.s_1069231
chr1.s_1069256
chr1.s_1069555
chr1.s_1069916
chr1.s_1069956
chr1.s_1070143
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for output files. Default: `<input_vcf>_id_subset`

If the user does not override them, defaults remain:


Default outputs:

- `<output_dir>/<prefix>.vcf`
- `<output_dir>/<prefix>_variant_ids.txt`
- `<output_dir>/<prefix>_summary.txt`

## Pre-Run Validation

Before running extraction, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `bcftools` or `python3` is not available inside `EasyGS_1`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `vcf_variant_extract_analysis(...)`, collect the required VCF path and variant ID list unless they are already available in the conversation.

Behavior rules:

- When asking for the variant ID list, always show the one-ID-per-line example format
- The VCF input must be `.vcf` or `.vcf.gz`
- The variant ID list may be a file path or inline text
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the input VCF
- the normalized variant ID list path
- the extracted VCF path
- the requested ID count
- the extracted variant count
