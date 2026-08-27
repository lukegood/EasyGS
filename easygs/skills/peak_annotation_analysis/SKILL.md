---
name: peak_annotation_analysis
description: Run ChIPseeker-based locus structural annotation for maize, wheat, or rice from a BED file using the matching user-managed GFF3 resource.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Peak Annotation Skill

Run maize, wheat, or rice locus structural annotation using the built-in
`peak_annotation_analysis` tool.

Species resources:

- `maize` (`Zea mays`), the legacy default:
  `~/.easygs/resources/peak_annotation_analysis/Zea_mays.B73_RefGen_v4.43_modify.gff3`
- `wheat` (`Triticum aestivum`):
  `~/.easygs/resources/peak_annotation_analysis/Taestivumcv_ChineseSpring_725_v2.1.gene.gff3`
- `rice` (`Oryza sativa`):
  `~/.easygs/resources/peak_annotation_analysis/Osativa_323_v7.0.gene.gff3`
- if `EASYGS_RESOURCES_DIR` is set, the tool uses that directory as the resource root

This is one complete workflow:

1. select and validate the species-specific GFF3 resource and BED loci file
2. verify that every BED chromosome name occurs in the selected GFF3
3. build a `TxDb` object from the GFF3 annotation resource
4. read the BED loci as peaks
5. run `annotatePeak()` with the chosen TSS window
6. export the annotation table and annotation pie chart
7. write a compact summary

Do not split this into separate public tools for `TxDb` construction, peak loading, or pie-chart
drawing.

## Tool-First Rule

Use `peak_annotation_analysis(...)` for execution.

## Required Inputs

- `bed`: BED file containing loci or peaks, with at least three tab-separated columns and
  coordinates satisfying `0 <= start < end`. Example:

```text
Chr1	207606062	207606063
Chr2	180017154	180017155
Chr2	191156851	191156852
Chr3	7214472	7214473
```

For wheat, chromosomes include a subgenome suffix, for example `Chr1A`, `Chr3B`, or `Chr7D`.

## Optional Parameters

- `species`: `maize`, `wheat`, or `rice`; default: `maize`
- `output_dir`: root directory for outputs; when omitted, the runtime supplies the current
  context's default
- `output_prefix`: basename/path prefix for outputs; default: BED stem, such as `locilist`
- `tss_upstream`: upstream TSS annotation window in bp; default: `2000`
- `tss_downstream`: downstream TSS annotation window in bp; default: `500`

The GFF3 path is intentionally not a public parameter. The tool selects it from the resource
directory according to `species` and reports the exact required path when it is missing.

Default outputs:

- `<output_dir>/<prefix>.peakanno.tsv`
- `<output_dir>/<prefix>.peakanno.png`
- `<output_dir>/<prefix>.peakanno_summary.txt`

## Pre-Run Validation

The tool checks:

- environment `EasyGS_1`
- executables `Rscript` and `python3`
- R packages `ChIPseeker`, `GenomicFeatures`, `ggplot2`, `txdbmaker`, and `dplyr`
- the selected species resource exists and contains GFF features
- the BED has valid rows and chromosome names matching the GFF3

Stop and report the exact error if any check fails.

## Parameter Collection Rules

Before calling `peak_annotation_analysis(...)`, collect the BED path and species unless already
available in the conversation. Omitting species intentionally keeps the legacy maize default.

Behavior rules:

- When asking for BED input, show three or four example rows and describe the format
- Do not ask the user for an annotation file; report the exact missing resource path instead
- Never expose a GFF3 path as a normal tool parameter
- Infer species only when unambiguous; otherwise ask whether the data are maize, wheat, or rice
- BED chromosome names must match the selected GFF3 exactly, such as `Chr1` for rice and `Chr1A`
  for wheat
- If no output location is mentioned, use the tool defaults
- Do not invent file paths

## Result Interpretation

After a successful run, highlight:

- the selected species and resource
- the output TSV and PNG paths
- the annotation row count
- the main annotation categories and counts when available
