---
name: vcf_stats
description: Generate VCF basic statistics and extracted summary lines using the built-in vcf_stats_analysis tool and bundled bcftools workflow.
metadata: {"easygs":{"emoji":"🧪","os":["linux"]}}
---

# VCF Basic Statistics Skill

Generate basic VCF statistics using the built-in `vcf_stats_analysis` tool.

This skill provides the workflow and interpretation rules. The actual execution should go through the `vcf_stats_analysis` tool instead of composing raw shell commands by hand. The tool validates the `EasyGS_1` environment before running.

## Tool-First Rule

Use the `vcf_stats_analysis` tool for execution.

Preferred sequence:

1. Collect or confirm the VCF path
2. Decide where outputs should be written
3. Call `vcf_stats_analysis(...)`

Only fall back to generic file tools for inspection and confirmation. Do not replace the dedicated tool with ad hoc `exec` commands unless you are debugging the bundled pipeline itself.

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion

## What the Tool Does

The `vcf_stats_analysis` tool wraps the bundled pipeline in `{baseDir}/scripts/vcf_stats.sh` and runs:

1. Environment validation (`EasyGS_1`)
2. `bcftools stats <vcf> > vcf_stats.txt`
3. `grep -E "^SN|^TSTV|^SiS|^# ST" vcf_stats.txt > cal.txt`

The extracted `cal.txt` keeps the summary sections for:

- overall summary lines (`SN`)
- transition/transversion statistics (`TSTV`)
- singleton and substitution categories (`SiS`)
- per-sample stats header rows (`# ST`)

## Required Inputs

- `vcf`: user-provided input `.vcf` or `.vcf.gz` path

Optional output controls:

- `output_dir`: write default outputs as `<output_dir>/vcf_stats.txt` and `<output_dir>/cal.txt`
- `stats_output`: explicit path for the raw stats file
- `summary_output`: explicit path for the extracted summary file

If no output paths are provided:

- it is acceptable to rely on the tool defaults

Default filenames remain:

- `vcf_stats.txt`
- `cal.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the environment check fails
- If the environment check fails, report it clearly and stop
- Do not fall back to hand-written shell commands to bypass this check

## Parameter Collection Rules

Before calling `vcf_stats_analysis(...)`, collect the required paths from the user if they are not already available in the conversation.

Required value to collect:

- VCF file path

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory. Never hardcode a dataset path.
- If the user provides a directory instead of a single file, inspect that directory and find likely `.vcf` or `.vcf.gz` candidates before asking a follow-up question.
- When multiple VCF candidates exist, ask the user to confirm which file should be used.
- If the user does not mention an output location, it is acceptable to use the tool defaults.
- If the user asks for specific filenames, pass them with `stats_output` and `summary_output`.
- Do not invent file paths.
- Confirm the final resolved paths before execution when there is any ambiguity.

## Preferred Tool Calls

Run with default outputs:

```text
vcf_stats_analysis(
  vcf="<user_provided_vcf_path>"
)
```

Run with an output directory:

```text
vcf_stats_analysis(
  vcf="<user_provided_vcf_path>",
  output_dir="<user_provided_output_dir>"
)
```

Run with explicit file paths:

```text
vcf_stats_analysis(
  vcf="<user_provided_vcf_path>",
  stats_output="<user_provided_stats_output>",
  summary_output="<user_provided_summary_output>"
)
```

## Result Interpretation

After a successful run:

- Point the user to `vcf_stats.txt` for the full `bcftools stats` output
- Point the user to `cal.txt` for the extracted key summary lines
- Summarize the preview briefly unless the user asks for a deeper interpretation
