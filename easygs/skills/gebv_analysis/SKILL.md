---
name: gebv_analysis
description: Estimate genomic breeding values with the built-in gebv_analysis tool and bundled GCTA reporting scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# GEBV Analysis Skill

Estimate genomic breeding values (GEBV) from an existing GCTA GRM prefix and a phenotype file using the built-in `gebv_analysis` tool.

This skill is dedicated to the GCTA `--reml --reml-pred-rand` workflow only.

## Tool-First Rule

Use `gebv_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled GEBV pipeline itself.

## Design Rule

Expose one complete end-to-end workflow to the user:

1. run GCTA REML random-effect prediction
2. extract the fourth column from `.indi.blp` as GEBV values
3. rank individuals and export the top percentage
4. generate a summary preview

If the implementation uses smaller internal steps, they must stay behind this single complete workflow.

## What the Tool Runs

```text
gcta64 --reml --grm <grm_prefix> --pheno <phenotype.txt> --reml-pred-rand --out <prefix>
```

Example:

```text
gcta64 --reml --grm ../1.遗传力计算/grm --pheno ../1.遗传力计算/test.phe.txt --reml-pred-rand --out gebv_result
```

## Required Inputs

- `grm_prefix`: GCTA GRM prefix without the `.grm.bin/.grm.N.bin/.grm.id` suffixes
- `pheno`: phenotype file used for GEBV estimation. Use a tab-delimited three-column file with `FID`, `IID`, and phenotype value, for example:

```text
FID	IID	PH
MG_49	MG_49	234.6
MG_50	MG_50	217.2
MG_51	MG_51	198.5
MG_52	MG_52	209.8
MG_53	MG_53	219.2
```

Optional output controls:

- `output_dir`: directory where outputs should be written
- `prefix`: basename for GCTA outputs
- `top_percent`: percentage of highest-GEBV individuals to export, default `10`

If the user does not override them, defaults remain:

- `prefix="gebv_result"`
- `top_percent=10`

Generated outputs:

- `<prefix>.hsq`
- `<prefix>.indi.blp`
- `<prefix>.log`
- `gebv_clean.txt` or `<prefix>_clean.txt`
- `breeding_analysis_top_<top_percent>percent.txt` or `<prefix>_top_<top_percent>percent.txt`
- `<prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `gcta64` is not available inside `EasyGS_2`
- If the environment check fails, report it clearly and stop
- Do not bypass the environment check with raw shell commands

## Parameter Collection Rules

Before calling `gebv_analysis(...)`, collect the required GRM prefix and phenotype path from the user unless they are already available in the conversation.

Behavior rules:

- The GRM prefix must correspond to a complete set of `.grm.bin`, `.grm.N.bin`, and `.grm.id` files
- The phenotype path must refer to a file
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `gebv_result`
- If the user does not mention a ranking threshold, use the default top `10%`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the generated `.hsq` and `.indi.blp` files
- the extracted GEBV table
- the selected top individuals file
- the total number of individuals ranked
- the number selected into the top group
- the leading individuals by GEBV
