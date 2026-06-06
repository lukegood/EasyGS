---
name: protein_function_annotation_analysis
description: Annotate maize proteins for a user gene list using user-managed longest-CDS and protein annotation resources, without running enrichment.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Protein Function Annotation Skill

Run protein function annotation using the built-in `protein_function_annotation_analysis` tool.

This skill is maize-only. It is designed for Zea mays gene IDs (`Zm...`) and reuses the same user-managed external resources as PFAM enrichment:

```text
~/.easygs/resources/pfam_enrichment_analysis/all_maize_longest_cds.txt
~/.easygs/resources/pfam_enrichment_analysis/all_maize_genes_proteins.fa.tsv
```

These files are not bundled with EasyGS because they are large reference resources. If `EASYGS_RESOURCES_DIR` is set, the tool uses that directory as the resource root instead of `~/.easygs/resources`.

## Tool-First Rule

Use `protein_function_annotation_analysis(...)` for execution.

## What the Tool Runs

The pipeline:

1. reads the user-provided `genelist.txt`
2. maps maize gene IDs to protein IDs with the longest-CDS resource
3. writes `gene_protein_map.tsv`
4. writes `protlist.txt`
5. extracts matching raw protein-annotation rows into `protlist.stranno.tsv`
6. writes a user-friendly `protein_function_annotation.tsv` with `gene_id` prepended
7. writes a compact summary text file

It does not run PFAM/domain enrichment.

## Required Inputs

- `genelist_txt`: user-provided gene list TXT. Example:

```text
Zm00001d031939
Zm00001d031940
Zm00001d031941
Zm00001d031942
```

## Optional Parameters

- `annotation_source`: annotation/library name from the maize proteins TSV column 4. Default: `all`. Use `Pfam` to return only PFAM rows.
- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `output_prefix`: result-file prefix. Default: `protein_function_annotation`

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/gene_protein_map.tsv`
- `<output_dir>/protlist.txt`
- `<output_dir>/protlist.stranno.tsv`
- `<output_dir>/protein_function_annotation.tsv`
- `<output_dir>/protein_function_annotation_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `awk` or `python3` is not available inside `EasyGS_2`
- The pipeline reads `all_maize_longest_cds.txt` from `~/.easygs/resources/pfam_enrichment_analysis/`
- The pipeline reads `all_maize_genes_proteins.fa.tsv` from `~/.easygs/resources/pfam_enrichment_analysis/`
- Do not ask the user for these resource paths during normal use
- If either resource file is missing, report the exact expected path and ask the user to place the file there
- This tool only supports maize data and maize gene IDs
- Do not invent file paths

## Parameter Collection Rules

Before calling `protein_function_annotation_analysis(...)`, collect the required gene list TXT unless it is already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- This tool only supports maize data and maize gene IDs

## Result Interpretation

After a successful run, the summary should highlight:

- the generated gene-protein map, protein list, raw annotation TSV, and user-friendly annotation TSV
- the number of input genes, mapped gene-protein pairs, unique proteins, annotated genes, annotated proteins, and annotation rows
- the top annotation sources when inferable
