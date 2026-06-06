---
name: region_r2_analysis
description: Run regional PLINK R2 analysis with the built-in region_r2_analysis tool and bundled reporting scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Region R2 Analysis Skill

Calculate pairwise R2 values within a specified genomic region from a PLINK BFILE dataset using the built-in `region_r2_analysis` tool.

This skill is dedicated to the PLINK `--r2` workflow on BFILE input with region constraints.

## Tool-First Rule

Use `region_r2_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled regional-R2 pipeline itself.

## What the Tool Runs

```text
plink --bfile <input_prefix> --r2 --chr <chr> --from-bp <start> --to-bp <end> --ld-window <n> --ld-window-r2 <threshold> --out <prefix>
```

Example:

```text
plink --bfile ~/easyGP/work/1.QC/4.格式转换与预处理/filter --r2 --from-bp 1000000 --to-bp 2000000 --chr 1 --ld-window 50 --ld-window-r2 0 --out region_r2_limited
```

Optional extension:

```text
--ld-window-kb 1000
```

## Required Inputs

- `bfile_prefix`: user-provided PLINK binary prefix with matching `.bed`, `.bim`, and `.fam` files
- `chromosome`: chromosome identifier for `--chr`
- `from_bp`: region start in base pairs
- `to_bp`: region end in base pairs

Optional controls:

- `ld_window`: maximum number of adjacent variants considered, default `50`
- `ld_window_kb`: optional maximum distance in kb
- `ld_window_r2`: minimum R2 threshold to report, default `0`
- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="region_r2_limited"`

Generated outputs:

- `<prefix>.ld`
- `<prefix>.log`
- `<prefix>.nosex`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `plink` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `region_r2_analysis(...)`, collect the required BFILE prefix and region coordinates from the user unless they are already available in the conversation.

Behavior rules:

- The BFILE prefix must come from the user or from inspecting a user-provided directory
- If the user provides a directory instead of a single prefix, inspect it and find likely `.bed/.bim/.fam` prefix candidates before asking a follow-up question
- If the user does not mention `ld_window`, `ld_window_kb`, or `ld_window_r2`, it is acceptable to use the defaults
- If the user does not mention an output prefix, it is acceptable to use the default `region_r2_limited`
- Do not invent file paths or coordinates

## Result Interpretation

After a successful run, the summary should highlight:

- region coordinates used for the R2 calculation
- total pair count in the `.ld` report
- unique variant count involved in the retained pairs
- mean and maximum R2
- mean pair distance when base-pair columns are available
