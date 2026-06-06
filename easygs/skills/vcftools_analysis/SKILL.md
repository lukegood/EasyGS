---
name: vcftools_analysis
description: Run any vcftools-supported VCF operation through the built-in vcftools_analysis tool using structured argument arrays, with EasyGS-managed input and output paths.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# VCFtools Analysis Skill

Run `vcftools` operations through the built-in `vcftools_analysis` tool.

This is the general-purpose vcftools entry point. Use it when the user asks for a vcftools operation that is not better served by a more specific EasyGS analysis tool.

## Tool-First Rule

Use `vcftools_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled vcftools runner itself.

## Relationship To Specific Tools

Prefer specific EasyGS tools when they match the request because they provide stronger summaries and workflow semantics:

- `allele_count_analysis` for `vcftools --counts`
- `allele_frequency_analysis` for `vcftools --freq`
- `nucleotide_diversity_analysis` for `--site-pi` or `--window-pi`
- `tajima_d_analysis` for `--TajimaD`

Use `vcftools_analysis` for other vcftools-supported functions, custom option combinations, and exploratory requests.

## What The Tool Runs

The tool constructs a safe argument-vector command, not a shell string.

For `.vcf.gz` input:

```text
vcftools --gzvcf <input.vcf.gz> <args...> --out <output_prefix>
```

For `.vcf` input:

```text
vcftools --vcf <input.vcf> <args...> --out <output_prefix>
```

The tool manages `--vcf`, `--gzvcf`, and `--out`. Do not include those flags in `args`.

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path
- `args`: array of vcftools arguments, for example `["--freq"]` or `["--maf", "0.05", "--recode", "--recode-INFO-all"]`

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for vcftools outputs

If the user does not override them, defaults remain:

- `prefix="vcftools"`

Generated outputs are determined by vcftools itself. The tool reports:

- `<prefix>.log`
- all files matching `<prefix>*`
- `<prefix>_summary.txt`

## Parameter Collection Rules

Before calling `vcftools_analysis(...)`, collect:

- the VCF path
- the vcftools arguments the user wants to run

Behavior rules:

- `args` must be an array of tokens, not a single shell command string
- Do not put `--vcf`, `--gzvcf`, or `--out` in `args`
- Do not invent vcftools options; use exactly the options requested by the user or already known from vcftools syntax
- If the user gives a plain command snippet like `vcftools --gzvcf a.vcf.gz --freq --out x`, convert it into `vcf="a.vcf.gz"`, `args=["--freq"]`, and `prefix="x"`
- If the user provides a directory instead of a single file, inspect it and find likely `.vcf` or `.vcf.gz` candidates before asking a follow-up question

## Result Interpretation

After a successful run, report:

- input VCF path
- vcftools args
- output prefix
- generated output files
- summary path

Do not over-interpret generic vcftools outputs unless their format is clear from the selected arguments.

