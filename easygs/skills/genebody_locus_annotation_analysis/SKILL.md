---
name: genebody_locus_annotation_analysis
description: Annotate loci that fall inside maize, wheat, or rice gene bodies using species gene-BED resources.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Genebody Locus Annotation Skill

Annotate user-provided loci that fall inside maize, wheat, or rice gene bodies using the
`genebody_locus_annotation_analysis` tool.

This is one complete workflow:

1. read the user-provided locus list
2. select the gene-BED resource for the requested species
3. convert locus IDs such as `chr1.s_201492` to single-base intervals while normalizing only
   the chromosome field
4. intersect those intervals with the selected gene-BED resource
5. write locus-to-gene pairs for genebody hits
6. write the corresponding gene list
7. write a compact summary

## Tool-First Rule

Use `genebody_locus_annotation_analysis(...)` for execution.

## What the Tool Runs

The bundled pipeline follows this logic:

```text
locus list -> species-aware chromosome normalization -> bedtools intersect
           -> locus-to-gene pairs -> gene list -> summary
```

The original locus ID is retained in the output. Only the temporary chromosome field used by
`bedtools` is normalized, so `chr1`, `Chr1`, and `1` can be matched to the selected resource.

## Required Inputs

- `locus_list`: user-provided TXT file. Each non-empty row should contain one locus ID in `chr<chrom>.s_<position>` format. Example:

```text
chr1.s_27738
chr1.s_201492
chr1.s_251434
chr1.s_294503
chr1.s_323280
```

## Resources

The tool selects one real resource file from:

```text
~/.easygs/resources/genebody_locus_annotation_analysis/
├── allV4gene.bed
├── allwheatgene.bed
└── allricegene.bed
```

The mapping is:

- `maize` -> `allV4gene.bed`
- `wheat` -> `allwheatgene.bed`
- `rice` -> `allricegene.bed`

`EASYGS_RESOURCES_DIR` may override the resource root. Each resource must be a real regular file,
not a symbolic link, with chromosome, start, end, and gene ID in columns 1 to 4. Do not ask the
user to provide a gene-BED path.

## Optional Parameters

- `species`: `maize`, `wheat`, or `rice`; default: `maize`
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
- The tool stops if `bedtools`, `python3`, `awk`, or `cut` is not available inside `EasyGS_2`
- The selected species gene-BED must exist in the resource directory and must be a real file
- Locus chromosome labels must occur in the selected resource after optional `chr` normalization
- The locus list must be supplied by the user and must not be invented

## Parameter Collection Rules

Before calling `genebody_locus_annotation_analysis(...)`, collect the required `locus_list` path
and species unless they are already available in the conversation. Keep `maize` as the default
when the user does not specify a species.

When asking for the required file, always provide the input example above and explain that each line should be one locus ID such as `chr1.s_201492`.

## Result Interpretation

After a successful run, highlight:

- the locus-to-gene output path
- the gene list output path
- the summary path
- the selected species
- the number of genebody site-gene pairs and unique genes when inferable
