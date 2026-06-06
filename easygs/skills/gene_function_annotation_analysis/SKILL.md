---
name: gene_function_annotation_analysis
description: Run maize GO/KEGG enrichment from a user-provided gene list TXT using a built-in Zm V4 gene-to-ENTREZ mapping CSV.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Gene Function Annotation Skill

Run GO and KEGG enrichment using the built-in `gene_function_annotation_analysis` tool.

This skill is maize-only. It is designed for Zea mays V4-style gene IDs (`Zm00001d...`) and uses the built-in mapping file:

- `easygs/skills/gene_function_annotation_analysis/scripts/entrez_Zm_gene_v4.csv`

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the user-provided gene list TXT
2. map the input gene list to ENTREZ IDs
3. fetch the requested Zea mays OrgDb from AnnotationHub
4. run KEGG enrichment
5. run GO enrichment
6. export text tables and PNG figures
7. write a compact summary

Do not split this into separate public tools for "ENTREZ mapping", "KEGG only", or "GO only". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `gene_function_annotation_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the user-provided gene list TXT
2. reads the built-in `gene_name -> ENTREZID` CSV
3. merges them and keeps non-null ENTREZ IDs
4. loads the requested OrgDb from AnnotationHub
5. runs `clusterProfiler::enrichKEGG()`
6. runs `clusterProfiler::enrichGO()`
7. writes `KEGG_Enrichment_Results.txt` and `KEGG_Enrichment_Results.png`
8. writes `GO_Enrichment_Results.txt` and `GO_Enrichment_Results.png`
9. writes a compact summary text file

## Required Inputs

- `genelist_txt`: user-provided gene list TXT with one gene ID per line. Example:

```text
Zm00001d031939
Zm00001d031940
Zm00001d031941
Zm00001d031942
```

- `annotationhub_id`: required AnnotationHub OrgDb resource ID. Recommended default: `AH119718`.
  Even if the user wants to use the default, they should still provide it explicitly.

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `gene_column`: gene ID column in the built-in mapping CSV. Default: `gene_name`
- `entrez_column`: ENTREZ ID column in the built-in mapping CSV. Default: `ENTREZID`
- `kegg_organism`: KEGG organism code. Must be `zma` (maize only). Default: `zma`
- `go_ontology`: GO ontology. Default: `ALL`
- `kegg_pvalue_threshold`: post-filter p-value threshold for KEGG results. Default: `0.1`
- `go_pvalue_threshold`: post-filter p-value threshold for GO results. Default: `0.05`

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/KEGG_Enrichment_Results.txt`
- `<output_dir>/KEGG_Enrichment_Results.png`
- `<output_dir>/GO_Enrichment_Results.txt`
- `<output_dir>/GO_Enrichment_Results.png`
- `<output_dir>/gene_function_annotation_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R packages are unavailable:
  `AnnotationHub`, `clusterProfiler`, `ggplot2`, `dplyr`
- The pipeline uses the built-in maize mapping CSV bundled in this skill
- Using `AnnotationHub` online/cache resources is acceptable

## Parameter Collection Rules

Before calling `gene_function_annotation_analysis(...)`, collect the required gene list TXT and `annotationhub_id` unless they are already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- The gene list input must be a text file
- `annotationhub_id` is required and should be provided explicitly by the user, even when using the recommended default `AH119718`
- This tool only supports maize data and maize gene IDs
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output KEGG and GO files
- the number of input genes and mapped ENTREZ IDs
- the number of significant KEGG and GO terms after filtering
