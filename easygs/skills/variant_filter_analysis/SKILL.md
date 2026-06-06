---
name: variant_filter_analysis
description: Run standalone PLINK variant filtering with the built-in variant_filter_analysis tool and bundled export/reporting scripts.
metadata: {"easygs":{"emoji":"🧹","os":["linux"]}}
---

# Variant Filter Analysis Skill

Filter samples and variants with PLINK, export a filtered VCF, and generate a concise filter summary using the built-in `variant_filter_analysis` tool.

This skill is dedicated to the filtering stage only. Use it directly when the user specifically wants `--mind/--geno/--hwe/--maf` filtering and filtered VCF export.

## Tool-First Rule

Use `variant_filter_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled filtering pipeline itself.

## What the Tool Runs

The tool wraps the bundled script in `{baseDir}/scripts/filter.sh` and runs:

```text
plink --vcf <vcf> --mind 0.05 --geno 0.05 --hwe 1e-4 --maf 0.0001 --make-bed --out <bed_prefix>
plink --bfile <bed_prefix> --export vcf --out <vcf_prefix>
bgzip <vcf_prefix>.vcf
tabix -p vcf <vcf_prefix>.vcf.gz
```

## Outputs

Outputs include:

- `<bed_prefix>.bed`
- `<bed_prefix>.bim`
- `<bed_prefix>.fam`
- `<bed_prefix>.log`
- `<bed_prefix>.nosex`
- `<vcf_prefix>.vcf`
- `<vcf_prefix>.log`
- `<vcf_prefix>.nosex`
- `<vcf_prefix>.vcf.gz`
- `<vcf_prefix>.vcf.gz.tbi`
- `<vcf_prefix>_summary.txt`

The summary should mention:

- retained sample count
- retained variant count
- filtered VCF export count
- applied thresholds

## Recommended Defaults

- `mind=0.05`
- `geno=0.05`
- `hwe=1e-4`
- `maf=0.0001`
- `bgzip_output=true`
- `tabix_index=true`

## Output Defaults

If the user does not specify output paths, it is acceptable to rely on the tool defaults.

## Parameter Collection Rules

Before calling `variant_filter_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths
- Do not silently change the thresholds unless the user asks for different values
- Do not create symlinks unless the user explicitly asks for a target directory

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion
