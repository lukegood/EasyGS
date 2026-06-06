---
name: mean_nucleotide_diversity_analysis
description: Compute the average nucleotide diversity (pi) from a user-provided vcftools .sites.pi file using the built-in mean_nucleotide_diversity_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Mean Nucleotide Diversity Analysis Skill

Compute the average nucleotide diversity (pi) from a user-provided `.sites.pi` file using the built-in `mean_nucleotide_diversity_analysis` tool.

This skill is dedicated to post-processing vcftools `*.sites.pi` output only.

## Tool-First Rule

Use `mean_nucleotide_diversity_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled mean-pi pipeline itself.

## What the Tool Computes

Equivalent shell logic:

```text
awk 'NR>1 {sum+=$3; count++} END {print "平均π: " sum/count}' nucleotide_diversity.sites.pi
```

Expected style of output:

```text
=== 核苷酸多样性(π) ===
平均π: 0.333921
```

## Required Inputs

- `sites_pi`: required user-provided path to `nucleotide_diversity.sites.pi` or another vcftools `.sites.pi` file

Optional output controls:

- `output_dir`: directory where the summary file should be written
- `prefix`: basename for the generated summary file

If the user does not override them, defaults remain:

- `prefix="mean_pi"`

Generated outputs:

- `<prefix>_summary.txt`

## Parameter Collection Rules

Before calling `mean_nucleotide_diversity_analysis(...)`, collect the required `.sites.pi` file path from the user unless it is already available in the conversation.

Behavior rules:

- The `.sites.pi` path is mandatory and must come from the user or from inspecting a user-provided directory
- Do not invent a `.sites.pi` path
- If the user does not mention an output location, it is acceptable to use the tool defaults
- If the user does not mention an output prefix, it is acceptable to use the default `mean_pi`

## Result Interpretation

After a successful run, the summary should highlight:

- the average pi value across numeric rows in column 3 of the `.sites.pi` file
