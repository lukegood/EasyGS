---
name: pca_analysis
description: Run PLINK PCA on a BFILE dataset and generate a PCA variance report using the built-in pca_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# PCA Analysis Skill

Run principal component analysis on a PLINK BED/BIM/FAM dataset using the built-in `pca_analysis` tool.

This skill is dedicated to PCA only.

## Tool-First Rule

Use `pca_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled PCA pipeline itself.

## What the Tool Runs

```text
plink --bfile <input_prefix> --pca 20 --out <prefix>
```

Example:

```text
plink --bfile data_ld_pruned --pca 20 --out data_pca_pruned
```

## Required Inputs

- `bfile_prefix`: input BED/BIM/FAM prefix

Optional output controls:

- `components`: number of principal components, default `20`
- `output_dir`: output directory; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for PCA outputs

If the user does not override them, defaults remain:

- `components=20`
- `prefix="data_pca_pruned"`

Generated outputs:

- `<prefix>.eigenval`
- `<prefix>.eigenvec`
- `<prefix>.log`
- `<prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `plink` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop

## Result Interpretation

After a successful run, the summary should highlight:

- the requested principal component count
- the total variance sum across eigenvalues
- the per-PC variance value and percentage
