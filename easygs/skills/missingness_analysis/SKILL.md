---
name: missingness_analysis
description: Run standalone PLINK missingness analysis with the built-in missingness_analysis tool and bundled reporting scripts.
metadata: {"easygs":{"emoji":"🧹","os":["linux"]}}
---

# Missingness Analysis Skill

Generate sample-level and variant-level missingness reports using the built-in `missingness_analysis` tool.

This skill is dedicated to the missingness stage only. Use it directly when the user specifically wants missing-rate analysis or a missingness report.

## Tool-First Rule

Use `missingness_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled missingness pipeline itself.

## What the Tool Runs

The tool wraps the bundled script in `{baseDir}/scripts/missingness.sh` and runs:

```text
plink --vcf <vcf> --missing --out <prefix>
```

Then it generates a text summary from:

- `<prefix>.imiss`
- `<prefix>.lmiss`

## Outputs

Outputs include:

- `<prefix>.imiss`
- `<prefix>.lmiss`
- `<prefix>.log`
- `<prefix>.nosex`
- `<prefix>_summary.txt`

The summary should mention:

- missingness distribution
- high-missingness samples
- high-missingness variants

## Recommended Defaults

- `sample_missing_alert_threshold=0.05`
- `variant_missing_alert_threshold=0.05`

## Output Defaults

If the user does not specify output paths, it is acceptable to rely on the tool defaults.

## Parameter Collection Rules

Before calling `missingness_analysis(...)`, collect the required VCF path from the user unless it is already available in the conversation.

Behavior rules:

- The VCF path must come from the user or from inspecting a user-provided directory
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths
- Do not silently change the thresholds unless the user asks for different values

## Job Follow-Up

If the tool returns a job ID:

- Tell the user the returned job ID
- Use `get_workflow_status(workflow_id=...)` to check progress
- Use `get_workflow_result(workflow_id=...)` after completion
