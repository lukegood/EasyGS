---
name: peak_annotation_analysis
description: Run maize-only ChIPseeker-based locus structural annotation from a BED file using the built-in Zea mays GFF3 annotation.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Peak Annotation Skill

Run maize locus structural annotation using the built-in `peak_annotation_analysis` tool.

Species scope:
- maize only (`Zea mays`)
- built-in annotation path: `/home/wlg/easyGP/pubdata/Zea_mays.B73_RefGen_v4.43_modify.gff3`

This should be treated as one complete workflow rather than separate user-facing steps, because the analysis depends on one tightly coupled chain:

1. validate the built-in maize GFF3 annotation and the BED loci file
2. build a `TxDb` object from the built-in GFF3 annotation
3. read the BED loci as peaks
4. run `annotatePeak()` with the chosen TSS window
5. export the annotation table and annotation pie chart
6. write a compact summary

Do not split this into separate public tools for `TxDb` construction, peak loading, or pie-chart drawing. Those stay internal inside one complete workflow.

## Tool-First Rule

Use `peak_annotation_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline:

1. reads the built-in maize GFF3 gene annotation file (`/home/wlg/easyGP/pubdata/Zea_mays.B73_RefGen_v4.43_modify.gff3`)
2. builds a `TxDb` object with `txdbmaker::makeTxDbFromGFF()`
3. reads the BED loci with `ChIPseeker::readPeakFile()`
4. runs `ChIPseeker::annotatePeak()` with a TSS region
5. writes `<prefix>.peakanno.tsv`
6. writes `<prefix>.peakanno.png`
7. writes a compact summary text file

## Required Inputs

- `bed`: BED file containing loci or peaks. Example:

```text
1	207606062	207606063
2	180017154	180017155
2	191156851	191156852
2	195873477	195873478
```

## Optional Parameters

- `output_dir`: root directory for outputs; when omitted, the runtime supplies the default for the current context
- `output_prefix`: basename/path prefix for outputs. Default: BED stem, such as `locilist`
- `tss_upstream`: upstream TSS annotation window in bp. Default: `2000`
- `tss_downstream`: downstream TSS annotation window in bp. Default: `500`

If the user wants any of these changed, ask them to provide the override explicitly instead of guessing.

Default output pattern:

- `<output_dir>/<prefix>.peakanno.tsv`
- `<output_dir>/<prefix>.peakanno.png`
- `<output_dir>/<prefix>.peakanno_summary.txt`

## Pre-Run Validation

Before running analysis, remember that the tool itself always checks whether the required environment exists:

- `EasyGS_1`

Behavior rules:

- The tool will stop automatically if the `EasyGS_1` environment is missing
- The tool will stop automatically if `Rscript` or `python3` is not available inside `EasyGS_1`
- The pipeline will stop automatically if the required R packages are unavailable:
  `ChIPseeker`, `GenomicFeatures`, `ggplot2`, `txdbmaker`, `dplyr`
- If the environment check fails, report it clearly and stop

## Parameter Collection Rules

Before calling `peak_annotation_analysis(...)`, collect the required BED path unless it is already available in the conversation.

Behavior rules:

- When asking for required input files, always provide data examples with 3 to 4 sample rows together with the format description
- If mentioning optional parameters, always tell the user the default values and remind them to provide overrides explicitly
- The loci input must be `.bed`
- Do not ask the user for an annotation file; this skill uses the built-in maize GFF3 annotation
- This skill is maize-only and does not support non-maize annotations
- If the user does not mention an output location, it is acceptable to use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, the summary should highlight:

- the output TSV and PNG paths
- the annotation row count
- the main annotation categories and their counts when inferable
