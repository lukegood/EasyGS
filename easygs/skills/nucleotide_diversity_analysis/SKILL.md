---
name: nucleotide_diversity_analysis
description: Run vcftools nucleotide-diversity analysis in site-pi or window-pi mode using the built-in nucleotide_diversity_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Nucleotide Diversity Analysis Skill

Calculate nucleotide diversity (pi) using the built-in `nucleotide_diversity_analysis` tool.

This skill supports both vcftools `--site-pi` and `--window-pi`.

## Tool-First Rule

Use `nucleotide_diversity_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled pipeline itself.

## What the Tool Runs

Whole-genome site-pi mode:

```text
vcftools --gzvcf <input.vcf.gz> --site-pi --out <prefix>
```

Window-pi mode:

```text
vcftools --gzvcf <input.vcf.gz> --window-pi <window_size> --out <prefix>
```

Examples:

```text
vcftools --gzvcf ../../CUBIC/filter.vcf.gz --site-pi --out nucleotide_diversity
vcftools --gzvcf ../../CUBIC/filter.vcf.gz --window-pi 100000 --out window_pi_100kb
```

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional controls:

- `mode`: `site` or `window`
- `window_size`: used only for `mode="window"`
- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `mode="site"` unless `window_size` is provided
- `window_size=100000` for window mode
- `prefix="nucleotide_diversity"` for site mode
- `prefix="window_pi_100kb"` for the default window mode

Generated outputs:

- site mode: `<prefix>.sites.pi` and `<prefix>.log`
- window mode: `<prefix>.windowed.pi` and `<prefix>.log`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `vcftools` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `nucleotide_diversity_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user asks for window-pi and does not specify a window size, it is acceptable to use the default `100000`
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the mode-specific default prefix
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- site mode: total rows, number of rows with numeric PI, mean PI, median PI, min PI, max PI
- window mode: total windows, number of windows with numeric PI, mean window PI, median window PI, min window PI, max window PI
