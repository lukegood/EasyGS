---
name: sample_subset_analysis
description: Keep or remove specified samples from a PLINK BFILE dataset and export subset PED/MAP, BED/BIM/FAM, and VCF outputs using the built-in sample_subset_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Sample Subset Skill

Subset a PLINK BED/BIM/FAM dataset by keeping or removing a specified sample list using the built-in `sample_subset_analysis` tool.

This skill is dedicated to sample keep/remove workflows only.

## Tool-First Rule

Use `sample_subset_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled subset pipeline itself.

## What the Tool Runs

For keep:

```text
plink --bfile <prefix> --keep <sample_list> --recode --out <prefix>
plink --file <prefix> --make-bed --out <prefix>_turn
plink --bfile <prefix>_turn --export vcf --out <prefix>
```

For remove:

```text
plink --bfile <prefix> --remove <sample_list> --recode --out <prefix>
plink --file <prefix> --make-bed --out <prefix>_turn
plink --bfile <prefix>_turn --export vcf --out <prefix>
```

## Required Sample List Format

The `sample_list` file must contain exactly two columns: `FID` and `IID`.

Examples:

```text
MG_890 MG_890
MG_1254 MG_1254
MG_689 MG_689
```

No extra explanation text should be inserted into the file itself.

## Recommended Defaults

- `action="keep"` when the user does not specify keep vs remove after prompting
- `prefix="kept_samples"` for keep
- `prefix="remaining_samples"` for remove

## Output Defaults

If the user does not specify output paths, it is acceptable to rely on the tool defaults.

## Parameter Collection Rules

Before calling `sample_subset_analysis(...)`, collect the required BFILE prefix and sample list path from the user unless they are already available in the conversation.

Behavior rules:

- Ask whether the user wants to keep or remove the listed samples when that is not already clear
- If the user does not specify keep vs remove after prompting, use the default `keep`
- Explicitly tell the user that the sample list file must be a two-column `FID IID` file
- Show the user an example format when discussing the sample list file:
  `MG_890 MG_890`
  `MG_1254 MG_1254`
  `MG_689 MG_689`
- Ask for output paths only when the user wants to override the defaults
- Do not invent file paths

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion
