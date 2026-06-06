---
name: population_structure_kinship_analysis
description: Run LD-pruned PCA, GRM construction, and ADMIXTURE as one combined workflow using the built-in population_structure_kinship_analysis tool and bundled scripts.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# Population Structure And Kinship Skill

Run the combined workflow for group structure partitioning and kinship calculation using the built-in `population_structure_kinship_analysis` tool.

This skill orchestrates multiple dedicated sub-steps:

- LD pruning
- extraction of non-linked SNPs into a new BFILE
- PCA on the LD-pruned dataset
- GRM construction
- ADMIXTURE cross-validation and best-K selection

## Tool-First Rule

Use `population_structure_kinship_analysis(...)` for execution.

Do not replace it with ad hoc shell commands unless you are debugging the bundled combined workflow itself.

## Required Inputs

- `bfile_prefix`: required input BED/BIM/FAM prefix, such as `filter`

Optional controls:

- `ld_bfile_prefix`: optional existing LD-pruned BFILE prefix to reuse for PCA
- `output_dir`: output directory; when omitted, the runtime supplies the default for the current context
- `ld_window_size`, `ld_step_size`, `ld_r2_threshold`
- `pca_components`
- `k_min`, `k_max`
- optional per-step prefixes

Recommended defaults:

- `ld_window_size=50`
- `ld_step_size=5`
- `ld_r2_threshold=0.2`
- `pca_components=20`
- `k_min=2`
- `k_max=10`
- `ld_prune_prefix="data_pruned"`
- `ld_bfile_output_prefix="data_ld_pruned"`
- `pca_prefix="data_pca_pruned"`
- `grm_prefix="grm"`

## Environment

The tool validates the `EasyGS_2` environment before execution.

It requires:

- `plink`
- `gcta64`
- `admixture`
- `python3`

## Result Interpretation

After a successful run, the final summary should highlight:

- the LD-pruned output prefix
- the PCA variance report
- the GRM output prefix
- the best K and CV error from ADMIXTURE
