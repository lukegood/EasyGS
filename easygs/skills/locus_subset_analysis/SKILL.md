---
name: locus_subset_analysis
description: Keep or remove specified loci from a PLINK BFILE dataset and export subset PED/MAP, BED/BIM/FAM, and VCF outputs using the built-in locus_subset_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Locus Subset Skill

Subset a PLINK BED/BIM/FAM dataset by keeping or removing specified loci using the built-in `locus_subset_analysis` tool.

This skill is dedicated to locus keep/remove workflows only.

## Tool-First Rule

Use `locus_subset_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled subset pipeline itself.

## What the Tool Runs

For extract:

```text
plink --bfile filter --extract egLoci.txt --recode --out baoliuweidian
plink --file baoliuweidian --make-bed --out baoliuweidian_turn
plink --bfile baoliuweidian_turn --export vcf --out baoliuweidian
```

For exclude:

```text
plink --bfile filter --exclude egLoci.txt --recode --out tichuweidian
plink --file tichuweidian --make-bed --out tichuweidian_turn
plink --bfile tichuweidian_turn --export vcf --out tichuweidian
```

## Required Loci Format

The loci list should contain one locus ID per line.

Example `extract` / `exclude` content:

```text
chr1.s_667117
chr1.s_915373
chr1.s_1022873
chr1.s_1065915
chr1.s_1069916
chr1.s_1102676
chr1.s_1154593
chr1.s_1172097
chr1.s_1173275
chr1.s_1240840
```

No extra explanation text should be inserted into the file itself.

## Recommended Defaults

- `bfile_prefix="filter"`
- `action="extract"` when the user does not specify extract vs exclude after prompting
- `prefix="baoliuweidian"` for extract
- `prefix="tichuweidian"` for exclude

## Output Defaults

If the user does not specify output paths, it is acceptable to rely on the tool defaults.

## Parameter Collection Rules

Before calling `locus_subset_analysis(...)`, collect the required locus list from the user unless it is already available in the conversation.

Behavior rules:

- Ask whether the user wants to keep/extract or remove/exclude the listed loci when that is not already clear
- If the user does not specify extract vs exclude after prompting, use the default `extract`
- Tell the user that the loci list is a required parameter and should be one locus ID per line
- Show the user the example `extract` format when discussing the `extract` parameter:
  `chr1.s_667117`
  `chr1.s_915373`
  `chr1.s_1022873`
  `chr1.s_1065915`
  `chr1.s_1069916`
  `chr1.s_1102676`
  `chr1.s_1154593`
  `chr1.s_1172097`
  `chr1.s_1173275`
  `chr1.s_1240840`
- Ask for `bfile_prefix`, output directory, or output prefix only when the user wants to override the defaults
- If the user is speaking Chinese, keep the parameter prompts in Chinese
- Do not invent file paths

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion
