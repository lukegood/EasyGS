---
name: ortholog_extraction_analysis
description: Extract maize, wheat, or rice ortholog rows by exact first-column gene matching using a species-specific EasyGS matrix resource.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Ortholog Extraction Skill

Extract ortholog rows for maize, wheat, or rice using the built-in
`ortholog_extraction_analysis` tool.

Species resources:

- `maize`, the legacy default:
  `~/.easygs/resources/ortholog_extraction_analysis/maize_ortholog_matrix.tsv`
- `wheat`:
  `~/.easygs/resources/ortholog_extraction_analysis/wheat_ortholog_matrix.tsv`
- `rice`:
  `~/.easygs/resources/ortholog_extraction_analysis/rice_ortholog_matrix.tsv`
- if `EASYGS_RESOURCES_DIR` is set, the tool uses that directory as the resource root

This is one complete workflow:

1. validate the user gene-list TXT
2. select and validate the source-species ortholog matrix resource
3. ignore blank gene-list rows and deduplicate requested IDs for matching
4. match each full gene ID exactly against the matrix's first column
5. preserve matrix row order and all duplicate relationship rows
6. export the matched TSV and a compact summary

Do not split filtering and summarization into separate public tools.

## Tool-First Rule

Use `ortholog_extraction_analysis(...)` for execution.

## Required Input

- `genelist_txt`: one source-species gene ID per line. Wheat example:

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

- `species`: `maize`, `wheat`, or `rice`; default: `maize`
- `output_dir`: output directory; the runtime supplies a context default when omitted
- `output_filename`: output TSV filename. By default a trailing `_genes` is removed, so
  `100_wheat_genes.txt` becomes `100_wheat.ortholog.tsv`; other stems are preserved

The ortholog matrix path is intentionally not public. The tool selects it from the resource
directory and reports the exact required path when missing.

Outputs:

- `<output_dir>/<derived-or-explicit-name>.ortholog.tsv`
- `<output_dir>/<output-tsv-stem>_summary.txt`

## Matching Semantics

The extraction uses exact first-column equality rather than `grep -f` substring matching. This
prevents blank patterns, prefix IDs, or IDs appearing only in a target-species column from
matching unrelated rows. If the same source gene occurs on multiple matrix rows, every row is
retained.

## Pre-Run Validation

The tool checks:

- environment `EasyGS_2`
- executable `python3`
- non-empty gene list
- selected matrix resource existence
- tab-delimited matrix with at least two columns
- first matrix header equals the selected species (`Maize`, `Wheat`, or `Rice`)

Stop and report the exact error if validation fails.

## Parameter Collection Rules

Collect the gene-list path and species unless already available. Omitting species intentionally
keeps the legacy maize default.

Behavior rules:

- When asking for a gene list, show three or four example rows
- Never ask for or expose a matrix path as a normal parameter
- Infer species only when unambiguous; otherwise ask whether the genes are maize, wheat, or rice
- Use tool defaults when no output location is requested
- Do not invent paths

## Result Interpretation

After a successful run, report:

- selected species and matrix resource
- output TSV and summary paths
- requested and unique requested gene counts
- matched row and matched unique gene counts
- missing gene count
