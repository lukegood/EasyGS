---
name: grm_analysis
description: Construct a genomic relationship matrix from a BFILE dataset using the built-in grm_analysis tool and bundled GCTA scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# GRM Analysis Skill

Construct a genomic relationship matrix (GRM) from a PLINK BED/BIM/FAM dataset using the built-in `grm_analysis` tool.

This skill is dedicated to GRM construction only.

## Tool-First Rule

Use `grm_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled GRM pipeline itself.

## What the Tool Runs

```text
gcta64 --bfile <input_prefix> --make-grm --out <prefix>
```

Example:

```text
gcta64 --bfile filter --make-grm --out grm
```

## Required Inputs

- `bfile_prefix`: input BED/BIM/FAM prefix

Optional output controls:

- `output_dir`: output directory; when omitted, the runtime supplies the default for the current context
- `prefix`: GRM output basename

If the user does not override them, defaults remain:

- `prefix="grm"`

Generated outputs:

- `<prefix>.grm.bin`
- `<prefix>.grm.id`
- `<prefix>.grm.N.bin`
- `<prefix>.log`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `gcta64` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
