---
name: pfam_enrichment_analysis
description: Extract candidate proteins from a gene list and run maize-only PFAM/domain enrichment using user-managed longest-CDS and proteins annotation resources.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# PFAM Enrichment Skill

Run PFAM/domain enrichment using the built-in `pfam_enrichment_analysis` tool.

This skill is maize-only. It is designed for Zea mays gene IDs (`Zm...`) and requires user-managed external resource files.

Default resource directory:

```text
~/.easygs/resources/pfam_enrichment_analysis/
```

Required resource files:

```text
~/.easygs/resources/pfam_enrichment_analysis/all_maize_longest_cds.txt
~/.easygs/resources/pfam_enrichment_analysis/all_maize_genes_proteins.fa.tsv
```

These files are not bundled with EasyGS because they are large reference resources. The user must download or prepare them manually and place them at the exact paths above. If `EASYGS_RESOURCES_DIR` is set, the tool uses that directory as the resource root instead of `~/.easygs/resources`.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the user-provided gene list TXT
2. map genes to protein IDs using the maize longest-CDS TXT resource
3. create `protlist.txt`
4. extract matching protein-annotation rows into `protlist.stranno.tsv`
5. filter the selected annotation source into an internal source-specific TSV
6. run hypergeometric enrichment on the selected annotation source
7. export complete and significant enrichment CSV files
8. write a compact summary

Do not split this into separate public tools for "protlist extraction", "annotation row extraction", or "PFAM enrichment only". Those stay internal inside one complete workflow.

## Tool-First Rule

Use `pfam_enrichment_analysis(...)` for execution.

## What the Tool Runs

The pipeline:

1. reads the user-provided `genelist.txt`
2. reads the maize longest-CDS mapping TXT from the user resource directory
3. extracts protein IDs into `protlist.txt`
4. extracts matching annotation rows into `protlist.stranno.tsv`
5. filters the selected annotation source from the maize proteins TSV resource into an internal source-specific TSV
6. runs hypergeometric enrichment
7. writes `<output_prefix>_all_pfam_enrichment.csv`
8. writes `<output_prefix>_sig_pfam.csv`
9. writes a compact summary text file

## Required Inputs

- `genelist_txt`: user-provided gene list TXT. Example:

```text
Zm00001d031939
Zm00001d031940
Zm00001d031941
Zm00001d031942
```

## Optional Parameters

- `background_protein_txt`: custom background protein list TXT. Default: use all annotated proteins from the selected annotation source
- `annotation_source`: annotation/library name from the maize proteins TSV column 4. Default: `Pfam`
- `min_count_in_candidates`: minimum candidate count required for significant reporting. Default: `5`
- `p_adjust_method`: p-value adjustment method. Default: `BH`
- `fdr_cutoff`: adjusted p-value cutoff. Default: `0.05`
- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `output_prefix`: result-file prefix. Default: `pfam_enrichment`

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/protlist.txt`
- `<output_dir>/protlist.stranno.tsv`
- `<output_dir>/<output_prefix>_<annotation_source>.source.tsv`
- `<output_dir>/pfam_enrichment_all_pfam_enrichment.csv`
- `<output_dir>/pfam_enrichment_sig_pfam.csv`
- `<output_dir>/pfam_enrichment_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `Rscript`, `awk`, or `python3` is not available inside `EasyGS_2`
- The pipeline reads `all_maize_longest_cds.txt` from `~/.easygs/resources/pfam_enrichment_analysis/`
- The pipeline reads `all_maize_genes_proteins.fa.tsv` from `~/.easygs/resources/pfam_enrichment_analysis/`
- Do not ask the user for these resource paths during normal use
- If either resource file is missing, report the exact expected path and ask the user to place the file there
- This tool only supports maize data
- Do not invent file paths

## Parameter Collection Rules

Before calling `pfam_enrichment_analysis(...)`, collect the required gene list TXT unless it is already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- This tool only supports maize data and maize gene IDs

## Result Interpretation

After a successful run, the summary should highlight:

- the generated `protlist.txt` and `protlist.stranno.tsv`
- the complete and significant enrichment CSV files
- the number of candidate proteins, annotated rows, enriched domains, and significant domains
