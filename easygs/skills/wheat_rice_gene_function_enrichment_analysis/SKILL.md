---
name: wheat_rice_gene_function_enrichment_analysis
description: Run offline GO and/or KEGG enrichment for wheat or rice from a user gene list using species-specific EasyGS resources.
metadata: {"easygs":{"emoji":"🌾","os":["linux"]}}
---

# Wheat/Rice Gene Function Enrichment Skill

Run wheat or rice GO/KEGG enrichment with the built-in
`wheat_rice_gene_function_enrichment_analysis` tool.

This is one public workflow with three execution modes: `ALL`, `GO`, and `KEGG`.
Do not expose gene-to-GO/KO mapping or annotation paths as ordinary user inputs.

## Resource Directory

Default directory:

```text
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/
```

Required user-managed resources:

```text
wheat_gene_KO_one2one.tsv
rice_gene_KO_one2one.tsv
taes_KEGG_annotation.txt
rice_KEGG_annotation.txt
wheat_gene_GO_one2one.tsv
rice_gene_GO_one2one.tsv
GO_term_table_2026.7.16.tsv
```

If `EASYGS_RESOURCES_DIR` is set, use that resource root instead. The tool selects
only the files required by the requested species and analysis type. Do not ask the
user for resource paths during normal use. If a resource is missing, report its exact
expected path.

## Tool-First Rule

Use `wheat_rice_gene_function_enrichment_analysis(...)` for execution.

## Required Inputs

- `genelist_txt`: one gene ID per non-empty line
- `species`: explicitly `wheat` or `rice`; never guess the species

Wheat example:

```text
TraesCS6A03G0926000
TraesCS3D03G0591600
TraesCS3B03G0806700
TraesCS1D03G0346300
```

Rice example:

```text
LOC_Os02g07880
LOC_Os01g19750
LOC_Os05g33910
LOC_Os07g42632
```

## Optional Parameters

- `analysis_type`: `ALL`, `GO`, or `KEGG`; default `ALL`
- `output_dir`: output root; the workflow runtime supplies a default when omitted
- `output_prefix`: common prefix; default is the species name

If the user asks for both GO and KEGG, use `ALL`. If the user explicitly asks for
only one branch, use `GO` or `KEGG`.

## Statistical Defaults

- complete result cutoff: p-value and q-value up to `1`
- significant result rule: `p < 0.1` and `q < 0.2`
- p-value adjustment: `BH`
- gene-set size: `5` to `500`
- plots: top 20 complete-result terms ordered by p-value

The significant output filename contains `p0.1`, but the summary must clearly state
that the workflow also requires `q < 0.2`.

## Environment and Validation

- environment: `EasyGS_1`
- executables: `Rscript`, `python3`
- R packages: `clusterProfiler`, `dplyr`, `ggplot2`
- validate the gene list, requested species, selected resource files, required table
  columns, bundled scripts, environment, and output prefix before execution
- always generate each requested PNG; use an explanatory placeholder for empty results

## Result Interpretation

Report:

- the species and analysis type
- input and mapped-gene counts
- complete and significant GO/KEGG term counts
- every requested output path
- the summary path
