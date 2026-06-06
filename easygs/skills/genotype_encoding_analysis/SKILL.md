---
name: genotype_encoding_analysis
description: Run PLINK --recodeA to encode genotypes as 0/1/2 additive dosage using the EasyGS_2 environment.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Genotype Encoding Analysis Skill

Convert PLINK genotype data to additive 0/1/2 encoding with the built-in `genotype_encoding_analysis` tool.

Default encoding meaning:

- two major alleles: `0`
- heterozygous genotype: `1`
- two minor alleles: `2`

This skill is intended for PLINK PED/MAP prefixes such as genotypes represented as `1 1`, `2 2`, `11`, `22`, `AA`, `TT`, or mixed allele labels. It also accepts PLINK BED/BIM/FAM prefixes when the input is already binary.

## Tool-First Rule

Use `genotype_encoding_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled genotype-encoding pipeline itself.

## What the Tool Runs

For PED/MAP input:

```text
plink --file <input_prefix> --recodeA --out <output_prefix>
```

For BED/BIM/FAM input:

```text
plink --bfile <input_prefix> --recodeA --out <output_prefix>
```

Example data prefix:

```text
/home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter
```

Example command shape:

```text
plink --file /home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter --recodeA --out filter
```

## Required Inputs

Collect exactly one input prefix from the user:

- `ped_prefix`: PLINK PED/MAP prefix with matching `.ped` and `.map` files
- `bfile_prefix`: PLINK BED/BIM/FAM prefix with matching `.bed`, `.bim`, and `.fam` files

Optional output controls:

- `output_dir`: directory where output files should be written; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs

If the user does not override them, defaults remain:

- `prefix="filter"`

Generated outputs:

- `<prefix>.raw`
- `<prefix>.log`
- `<prefix>.nosex` when PLINK creates it
- `<prefix>_summary.txt`

## Pre-Run Validation

The tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The input prefix must come from the user or from inspecting a user-provided directory
- If the user has not provided a path, ask for it and show the example prefix above
- Do not silently use `/home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter` unless the user explicitly chooses that example
- Do not invent file paths, prefixes, or output directories
- The tool will stop automatically if `EasyGS_2` is missing
- The tool will stop automatically if `plink` or `python3` is not available inside `EasyGS_2`
- Do not bypass the environment check with raw shell commands

## Result Interpretation

After a successful run, report:

- the `.raw` additive genotype matrix path
- sample count and encoded marker count from the summary
- PLINK log path
- summary file path
