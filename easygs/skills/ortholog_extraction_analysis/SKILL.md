---
name: ortholog_extraction_analysis
description: Extract ortholog rows from a user-provided maize ortholog matrix TSV using a user-provided gene list TXT and export a matched .ortholog.tsv file.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Ortholog Extraction Skill

Run ortholog extraction using the built-in `ortholog_extraction_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the user-provided gene list TXT
2. validate the user-provided ortholog matrix TSV
3. extract matching rows with `grep -f`
4. export `<genelist_stem>.ortholog.tsv`
5. write a compact summary

Do not split this into separate public tools for gene-list filtering and TSV extraction. Those stay internal inside one complete workflow.

## Tool-First Rule

Use `ortholog_extraction_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the user-provided `genelist.txt`
2. reads the user-provided `maize_ortholog_matrix.tsv`
3. runs fixed-string row extraction with `grep -F -f`
4. writes `<genelist_stem>.ortholog.tsv`
5. writes a compact summary text file

## Required Inputs

- `genelist_txt`: user-provided gene list TXT. Example:

```text
Zm00001d031939
Zm00001d031940
Zm00001d031941
Zm00001d031942
```

- `ortholog_matrix_tsv`: user-provided maize ortholog matrix TSV. Example:

```text
Maize	Arabidopsis	sorghum	Brachypodium	rice	setaria
GRMZM5G800096	ATCG01050	ABK79546,SORBI_K036300	NA	NA	Si020851m.g
GRMZM5G800101	NA	ABK79539	BRADI4G37052	OS04G0473025	NA
GRMZM5G800457	NA	NA	NA	NA	Si020789m.g
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `output_filename`: output TSV filename. Default: `<genelist_stem>.ortholog.tsv`

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/<genelist_stem>.ortholog.tsv`
- `<output_dir>/<genelist_stem>.ortholog_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `grep` or `python3` is not available inside `EasyGS_2`
- All required local files must be explicitly supplied by the user
- Do not invent file paths
- Do not hide required local files inside the script

## Parameter Collection Rules

Before calling `ortholog_extraction_analysis(...)`, collect the required gene list TXT and ortholog matrix TSV unless they are already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- All required files must be explicitly supplied by the user and must not be hidden in the script

## Result Interpretation

After a successful run, the summary should highlight:

- the generated ortholog TSV path
- the requested gene count
- the matched ortholog-row count
- the matched maize-gene count when inferable
