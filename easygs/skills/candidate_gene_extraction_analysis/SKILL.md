---
name: candidate_gene_extraction_analysis
description: Extract candidate genes from a user-provided BED file by LD-window expansion and gene-annotation intersection using the built-in candidate_gene_extraction_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Candidate Gene Extraction Skill

Run candidate gene extraction using the built-in `candidate_gene_extraction_analysis` tool.

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the user-provided BED loci file
2. expand each locus interval by the chosen LD distance
3. validate the user-provided gene annotation BED file
4. run `bedtools intersect` between expanded loci and gene annotations
5. export the extended BED file and `genelist.txt`
6. write a compact summary

Do not split this into separate public tools for BED expansion, GFF-to-BED conversion, or `bedtools` intersection. Those stay internal inside one complete workflow.

## Tool-First Rule

Use `candidate_gene_extraction_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the user-provided BED file
2. expands each interval by the chosen LD distance
3. uses the user-provided gene annotation BED file
4. runs `bedtools intersect`
5. writes `<bed_stem>.extend.bed`
6. writes `genelist.txt`
7. writes a compact summary text file

## Required Inputs

- `bed`: user-provided BED file containing loci to expand. Example:

```text
1	207606062	207606063
2	180017154	180017155
2	191156851	191156852
2	195873477	195873478
```

- `gene_bed`: user-provided gene interval BED file with gene IDs in column 4. Example:

```text
1	44288	49837	Zm00001d027230
1	50876	55716	Zm00001d027231
1	92298	95134	Zm00001d027232
1	111654	118312	Zm00001d027233
```

## Optional Parameters

- `ld_distance`: LD expansion distance in bp. Default: `50000`
- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/<bed_stem>.extend.bed`
- `<output_dir>/genelist.txt`
- `<output_dir>/genelist_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_2`

Behavior rules:

- The tool will stop automatically if the `EasyGS_2` environment is missing
- The tool will stop automatically if `bedtools`, `python3`, or `awk` is not available inside `EasyGS_2`
- `gene_bed` is mandatory and must be supplied explicitly by the user
- `gene_bed` must be a BED-like file with at least 4 tab-separated columns and gene IDs in column 4
- Do not rely on hidden default gene annotation files inside the script

## Parameter Collection Rules

Before calling `candidate_gene_extraction_analysis(...)`, collect the required BED path and gene annotation BED path unless they are already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- The loci input must be `.bed`
- The gene annotation BED input must also be provided explicitly by the user
- Do not invent file paths
- The BED input is user-provided and must never be hardcoded
- All required files must be explicitly supplied by the user and must not be hidden in the script

## Result Interpretation

After a successful run, the summary should highlight:

- the expanded BED output path
- the `genelist.txt` path
- the LD distance used
- the total and unique candidate-gene counts when inferable
