---
name: admixture_analysis
description: Run ADMIXTURE across a K range and summarize the best K using the built-in admixture_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# ADMIXTURE Analysis Skill

Run ADMIXTURE with cross-validation on a PLINK BED/BIM/FAM dataset using the built-in `admixture_analysis` tool.

This skill is dedicated to population-structure analysis only.

## Tool-First Rule

Use `admixture_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled ADMIXTURE pipeline itself.

## What the Tool Runs

Equivalent shell structure:

```text
for K in 2 3 4 5 6 7 8 9 10; do
  admixture --cv filter.bed $K | tee log${K}.out
done
```

The tool then parses `CV error` lines to find the best K and writes `best_k_result.txt`.

## Required Inputs

- `bfile_prefix`: input BED/BIM/FAM prefix

Optional output controls:

- `k_min`: minimum K, default `2`
- `k_max`: maximum K, default `10`
- `output_dir`: output directory; when omitted, the runtime supplies the default for the current context
- `prefix`: dataset basename used for generated `.Q/.P` files, defaulting to the input basename

Generated outputs:

- `log<K>.out`
- `<prefix>.<K>.Q`
- `<prefix>.<K>.P`
- `best_k_result.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `admixture` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
