---
name: genebody_locus_annotation_analysis
description: Annotate loci that fall inside maize V4 gene bodies from a locus-list TXT using the built-in allV4gene.bed and the genebody_locus_annotation_analysis tool.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Genebody Locus Annotation Skill

Annotate user-provided loci that fall inside maize V4 gene bodies using the built-in `genebody_locus_annotation_analysis` tool.

This is one complete workflow:

1. read the user-provided locus list
2. convert locus IDs such as `chr1.s_201492` to single-base BED intervals
3. intersect those intervals with the built-in `allV4gene.bed`
4. write locus-to-gene pairs for genebody hits
5. write the corresponding gene list
6. write a compact summary

## Tool-First Rule

Use `genebody_locus_annotation_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline follows this logic:

```sh
awk -F '[.]s_' '{print $1"\t"$2"\t"$2+1"\t"$0}' locus_list.txt \
  | sed 's/chr//g' \
  | bedtools intersect -a - -b allV4gene.bed -wa -wb \
  | cut -f4,8 \
  | sed 's/^/chr/g'
```

Then it writes the second column of the locus-to-gene output as the gene list.

## Required Inputs

- `locus_list`: user-provided TXT file. Each non-empty row should contain one locus ID in `chr<chrom>.s_<position>` format. Example:

```text
chr1.s_27738
chr1.s_201492
chr1.s_251434
chr1.s_294503
chr1.s_323280
```

The gene-body BED file is built in:

- `allV4gene.bed`

Do not ask the user to provide `allV4gene.bed`.

## Optional Parameters

- `output_dir`: output directory; when omitted, the runtime supplies the default for the current context

Default outputs:

- `<output_dir>/位于genebody的位点及其对应的基因.txt`
- `<output_dir>/位于genebody的基因.txt`
- `<output_dir>/genebody_locus_annotation_summary.txt`

## Pre-Run Validation

The tool checks the required environment:

- `EasyGS_2`

Behavior rules:

- The tool stops if `EasyGS_2` is missing
- The tool stops if `bedtools`, `python3`, `awk`, `sed`, or `cut` is not available inside `EasyGS_2`
- The built-in `allV4gene.bed` must exist inside the skill scripts directory
- The locus list must be supplied by the user and must not be invented

## Parameter Collection Rules

Before calling `genebody_locus_annotation_analysis(...)`, collect the required `locus_list` path unless it is already available in the conversation.

When asking for the required file, always provide the input example above and explain that each line should be one locus ID such as `chr1.s_201492`.

## Result Interpretation

After a successful run, highlight:

- the locus-to-gene output path
- the gene list output path
- the summary path
- the number of genebody site-gene pairs and unique genes when inferable
