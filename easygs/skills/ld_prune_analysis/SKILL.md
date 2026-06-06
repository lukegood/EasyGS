---
name: ld_prune_analysis
description: Run standalone PLINK LD pruning using the built-in ld_prune_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧹","os":["linux"]}}
---

# LD Prune Analysis Skill

Use the built-in LD-prune analysis tool instead of hand-written shell commands.

This skill is dedicated to LD pruning only.

The tool validates the `EasyGS_2` environment before execution.

Missingness and variant filtering have been split into dedicated skills and tools:

- `missingness_analysis`
- `variant_filter_analysis`

## Tool-First Rule

Use the dedicated analysis tools for execution:

- `ld_prune_analysis(...)`

Do not replace these with ad hoc `exec` commands unless you are debugging the bundled pipeline scripts themselves.

## Workflow Discipline

For a general "do QC" request on a VCF file, prefer this staged order:

1. run the standalone `missingness_analysis` skill/tool first when the user needs a missingness report
2. review the missingness result
3. run the standalone `variant_filter_analysis` skill/tool when the user needs `--mind/--geno/--hwe/--maf` filtering
4. suggest `ld_prune_analysis` as the next step when appropriate

Behavior rules:

- Do not silently change filtering thresholds
- Do not invent output directories, file prefixes, or symlink targets
- If a stage fails, stop the workflow and report the failure instead of continuing to later stages
- Use `vcf_stats_analysis` only when the user explicitly wants a dataset overview or when a concise overview is genuinely helpful

## Output Defaults

If the user does not specify output paths, it is acceptable to rely on the tool defaults.

## Stage 1: LD Pruning

Use `ld_prune_analysis(...)` to run:

```text
plink --vcf <vcf> --indep-pairwise 50 5 0.2 --out <prefix>
```

Recommended defaults:

- `window_size=50`
- `step_size=5`
- `r2_threshold=0.2`

If the user already has PLINK BED files from the filtering step, it is acceptable to use `bfile_prefix` instead of `vcf`.

## Parameter Collection Rules

Before execution:

- Collect the VCF path from the user unless it is already available in the conversation
- Ask for thresholds only when the user wants to override the defaults
- Ask for output paths only when the user wants to override the defaults
- Do not invent file paths

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion
