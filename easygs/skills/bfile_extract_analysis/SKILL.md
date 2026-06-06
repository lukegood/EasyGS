---
name: bfile_extract_analysis
description: Extract variants from a PLINK BFILE into a new BED/BIM/FAM dataset using the built-in bfile_extract_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# BFILE Extract Analysis Skill

Extract variants listed in a file from a PLINK BED/BIM/FAM dataset using the built-in `bfile_extract_analysis` tool.

This skill is dedicated to BFILE variant extraction only.

## Tool-First Rule

Use `bfile_extract_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled extraction pipeline itself.

## What the Tool Runs

```text
plink --bfile <input_prefix> --extract <extract_file> --make-bed --out <prefix>
```

Example:

```text
plink --bfile filter --extract data_pruned.prune.in --make-bed --out data_ld_pruned
```

## Required Inputs

- `bfile_prefix`: input BED/BIM/FAM prefix
- `extract_file`: required variant list file, typically `data_pruned.prune.in`

Optional output controls:

- `output_dir`: output directory; when omitted, the runtime supplies the default for the current context for the extracted BED/BIM/FAM files
- `prefix`: basename for the extracted dataset

If the user does not override them, defaults remain:

- `prefix="data_ld_pruned"`

Generated outputs:

- `<prefix>.bed`
- `<prefix>.bim`
- `<prefix>.fam`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `plink` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `bfile_extract_analysis(...)`, collect both the BFILE prefix and the extract file path unless they are already available in the conversation.

Behavior rules:

- Do not invent file paths
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `data_ld_pruned`
