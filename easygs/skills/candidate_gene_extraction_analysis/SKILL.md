---
name: candidate_gene_extraction_analysis
description: Extract candidate genes for maize, wheat, or rice from LD-expanded BED loci using species gene-BED resources.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# Candidate Gene Extraction Skill

Use the built-in `candidate_gene_extraction_analysis` tool to extract genes overlapping
LD-expanded loci for maize, wheat, or rice.

Treat this as one complete workflow:

1. validate the user BED and LD distance
2. select the species gene-BED resource
3. confirm that chromosome names match the resource
4. expand each input interval on both sides
5. intersect expanded intervals with genes
6. export the expanded BED, sorted unique gene list, detailed matches, and summary

Do not expose gene-BED resource paths or split expansion and intersection into separate public
tools.

## Tool-First Rule

Use `candidate_gene_extraction_analysis(...)` for execution.

## Resources

The tool selects one real resource file from:

```text
~/.easygs/resources/candidate_gene_extraction_analysis/
├── allV4gene.bed
├── allwheatgene.bed
└── allricegene.bed
```

The mapping is:

- `maize` -> `allV4gene.bed`
- `wheat` -> `allwheatgene.bed`
- `rice` -> `allricegene.bed`

`EASYGS_RESOURCES_DIR` may override the resource root. The gene BED must have chromosome, start,
end, and gene ID in columns 1 to 4.

## Required Input

- `bed`: user-provided BED with at least three tab-separated columns. Wheat example:

```text
Chr1A	207606062	207606063
Chr3A	180017154	180017155
Chr4B	191156851	191156852
```

Rice example:

```text
Chr1	207606062	207606063
Chr2	180017154	180017155
Chr3	7214472	7214473
```

BED coordinates must satisfy `0 <= start < end`. Chromosome labels must occur in the selected
species resource.

## Optional Parameters

- `species`: `maize`, `wheat`, or `rice`; default: `maize`
- `ld_distance`: expansion on each side in bp; default: `50000`; use `100000` for the supplied
  wheat/rice examples
- `output_dir`: output directory; runtime context supplies the default when omitted
- `output_prefix`: filename prefix; default: the input BED stem

The gene BED is not a public parameter. Ask for `species`, not a reference-file path.

## Outputs

For `output_prefix=testwheat`:

- `testwheat.extend.bed`: three-column LD-expanded loci
- `testwheat.txt`: lexically sorted unique candidate gene IDs
- `testwheat.detailed.tsv`: seven-column locus-to-gene overlap rows
- `testwheat_summary.txt`: inputs and row counts

The detailed rows consist of the three expanded-locus columns followed by the four gene-BED
columns.

## Runtime and Validation

The workflow runs in `EasyGS_2` and requires `bedtools`, `python3`, `awk`, and `sort`.

It stops before execution when:

- `species` is unsupported
- the BED or resource is missing or malformed
- coordinates are invalid
- input chromosome labels are absent from the selected species resource
- required environment tools are unavailable

After a successful run, report all four output paths, the LD distance, species, detailed overlap
count, and unique candidate-gene count.
