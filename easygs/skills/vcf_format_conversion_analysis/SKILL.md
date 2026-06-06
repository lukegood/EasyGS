---
name: vcf_format_conversion_analysis
description: Convert between VCF files and PLINK BED/BIM/FAM, PED/MAP, or exported VCF outputs using the built-in vcf_format_conversion_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🔁","os":["linux"]}}
---

# VCF Format Conversion Skill

Convert between VCF and PLINK file families using the built-in `vcf_format_conversion_analysis` tool.

This skill is dedicated to format conversion only. Use it when the user specifically wants:

- `vcf -> bed/bim/fam`
- `vcf -> ped/map`
- `bed/bim/fam -> vcf`
- `ped/map -> bed/bim/fam`

## Tool-First Rule

Use `vcf_format_conversion_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled conversion pipeline itself.

## What the Tool Runs

For BED/BIM/FAM output:

```text
plink --vcf <vcf> --double-id --make-bed --out <prefix>
```

For PED/MAP output:

```text
plink --vcf <vcf> --allow-extra-chr --recode --out <prefix>
```

For VCF export from PLINK BED/BIM/FAM input:

```text
plink --bfile <prefix> --export vcf --out <prefix>
```

For BED/BIM/FAM output from PED/MAP input:

```text
plink --file <prefix> --make-bed --out <prefix>
```

## Supported Target Formats

- `bed`: generate `<prefix>.bed`, `<prefix>.bim`, `<prefix>.fam`
- `ped`: generate `<prefix>.ped`, `<prefix>.map`
- `vcf`: generate `<prefix>.vcf`

## Supported Input Patterns

- `vcf=...` with `target_format="bed"` or `target_format="ped"`
- `bfile_prefix=...` with `target_format="vcf"`
- `ped_prefix=...` with `target_format="bed"`

## Recommended Defaults

- If the source input is `vcf` and the user does not specify a target format, default to `target_format="bed"`
- If the source input is `bfile_prefix` and the user does not specify a target format, default to `target_format="vcf"`
- If the source input is `ped_prefix` and the user does not specify a target format, default to `target_format="bed"`
- `prefix="filter"` for BED/PED outputs
- `prefix="filter_turn"` for exported conversions from BFILE or PED input
- `double_id=true` for `bed`
- `allow_extra_chr=true` for `ped`

## Output Defaults

If the user does not specify output paths, it is acceptable to rely on the tool defaults.

## Parameter Collection Rules

Before calling `vcf_format_conversion_analysis(...)`, collect the required input path from the user unless it is already available in the conversation.

Behavior rules:

- Collect `vcf` when the source file is a VCF/VCF.GZ
- Collect `bfile_prefix` when the source is PLINK BED/BIM/FAM
- Collect `ped_prefix` when the source is PLINK PED/MAP
- Ask which target format the user wants when it is not already clear from the conversation
- If the user does not provide a target format after prompting, use `bed` for VCF or PED input and `vcf` for BFILE input
- Ask about `double_id` or `allow_extra_chr` only when the user wants to override the defaults
- Ask for output paths only when the user wants to override the defaults
- Do not invent file paths

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion
