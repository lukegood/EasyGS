---
name: cvf_split_analysis
description: Generate a cross-validation fold CSV from a user-provided one-column material LIST TXT using the built-in cvf_split_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# CVF Split Skill

Generate a cross-validation fold CSV from a material LIST TXT using the built-in `cvf_split_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the user-provided LIST TXT
2. read the first line as the sample column name, and require it to be a supported ID header
3. read one material ID per line from the remaining rows
4. shuffle the samples with a reproducible random seed
5. assign folds from `1..k` as evenly as possible
6. export the CVF CSV and a compact summary

Do not split this into separate public tools for "reading LIST", "shuffling samples", or "writing fold labels". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `cvf_split_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the user-provided LIST TXT
2. keeps the first non-empty line as the sample column name
3. requires the sample column name to be one of `ID`, `list_id`, `sample_id`, `line_id`, `material_id` and their compact lowercase variants
4. treats each remaining non-empty line as one material ID
5. validates duplicate IDs, empty IDs, and fold count
6. shuffles the sample order with the requested seed
7. assigns fold labels in round-robin order from `1` to `k`
8. writes the CVF CSV
9. writes a compact summary text file

## Required Inputs

- `list_txt`: path to the one-column material LIST TXT. The first line must be a supported sample column name such as `ID` or `list_id`, and each remaining line must contain one material ID. Example:

```text
ID
MG_001
MG_002
MG_003
MG_004
```

## Optional Parameters

- `k`: number of folds. Default: `10`
- `seed`: random seed used for reproducible shuffling. Default: `42`
- `cv_column`: fold column name in the output CSV. Default: `cv_1`
- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `prefix`: basename for outputs. Default: `<list_stem>_cvf_k<k>_seed<seed>`

Default outputs:

- `<output_dir>/<prefix>.csv`
- `<output_dir>/<prefix>_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_3`

Behavior rules:

- The tool will stop automatically if the `EasyGS_3` environment is missing
- The tool will stop automatically if `python3` is not available inside `EasyGS_3`
- The LIST input must be a `.txt` file
- The first non-empty line must be one of the supported ID headers such as `ID`, `list_id`, `sample_id`, `line_id`, or `material_id`
- The LIST file must contain a header and at least one material ID
- The material IDs must be unique
- The sample count must be greater than or equal to `k`

## Parameter Collection Rules

Before calling `cvf_split_analysis(...)`, collect the required LIST TXT path from the user unless it is already available in the conversation.

Behavior rules:

- When asking for the required input file, always provide a data example with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- If the user does not mention an output location, it is acceptable to use the tool defaults. In background workflows, the actual output will normally be written under `~/.easygs/workflows/runs/<workflow_id>/actions/<action_id>/`
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the input LIST path
- the sample column name
- the CV column name
- the fold count and random seed
- the output CSV path
- the sample count and per-fold counts
