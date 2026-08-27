---
name: pfam_enrichment_analysis
description: Run PFAM/domain enrichment for maize, wheat, or rice from a gene list using species-specific EasyGS resources and streaming InterProScan preprocessing.
metadata: {"easygs":{"emoji":"🌱","os":["linux"]}}
---

# PFAM Enrichment Skill

Run maize, wheat, or rice PFAM/domain enrichment with the built-in
`pfam_enrichment_analysis` tool.

Resource directory:

```text
~/.easygs/resources/pfam_enrichment_analysis/
```

Species resources:

- maize, the legacy default:
  - `all_maize_longest_cds.txt`
  - `all_maize_genes_proteins.fa.tsv`
- wheat:
  - `wheat_interpro.tsv`
- rice:
  - `Osativa_323_v7.0.protein_primaryTranscriptOnly.fa.tsv`

If `EASYGS_RESOURCES_DIR` is set, that directory replaces `~/.easygs/resources`.

This is one complete workflow:

1. validate the gene list and select species resources
2. for maize, map genes to longest-CDS protein IDs using the legacy mapping
3. for wheat/rice, normalize numeric transcript suffixes such as `.1`
4. stream the large InterProScan file and retain candidate annotations plus compact PFAM rows
5. use all PFAM-annotated IDs as the default background, or a user background when supplied
6. calculate hypergeometric and Fisher p-values, fold enrichment, and adjusted p-values
7. export all/significant CSV files, candidate annotations, and a summary

Do not expose reference-resource paths or split preprocessing and enrichment into separate public
tools.

## Tool-First Rule

Use `pfam_enrichment_analysis(...)` for execution.

## Required Input

- `genelist_txt`: one gene ID per line. Wheat example:

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
- `background_protein_txt`: optional gene/protein ID background; default: all PFAM-annotated IDs
- `annotation_source`: InterProScan analysis/library in column 4; default: `Pfam`
- `min_count_in_candidates`: minimum `k` for significant results; default: `5` for maize and
  `2` for wheat/rice
- `p_adjust_method`: method passed to R `p.adjust`; default: `BH`
- `fdr_cutoff`: adjusted-p cutoff; default: `0.05`
- `output_dir`: output directory; runtime context supplies a default when omitted
- `output_prefix`: default `pfam_enrichment` for maize, `wheat_pfam_enrichment` for wheat, and
  `rice_pfam_enrichment` for rice

## Outputs

Primary outputs:

- `<prefix>_all_pfam_enrichment.csv`
- `<prefix>_sig_pfam.csv`
- `<prefix>_summary.txt`

Supporting outputs:

- `protlist.txt`
- `protlist.stranno.tsv`
- `<prefix>_<annotation_source>.source.tsv`

For wheat/rice, the all-results schema follows the original workflow:
`pfam,K,k,p_hyper,p_fisher,FoldEnrichment,p_adj,negLog10P,negLog10FDR`.

## Large-File Rule

The wheat and rice InterProScan resources are multi-gigabyte files. Never load either entire raw
file into Python or R memory. The bundled preprocessing script reads one line at a time and writes
a compact five-column source table before enrichment.

## Pre-Run Validation

The tool checks:

- environment `EasyGS_2`
- executables `Rscript`, `awk`, and `python3`
- gene-list ID prefix matching the selected species
- required resource existence and at least five TSV columns
- maize longest-CDS mapping when `species=maize`
- valid count/FDR parameters

Stop and report the exact error when validation fails.

## Parameter Collection Rules

Collect the gene-list path and species unless already available. Omitting species intentionally
keeps the legacy maize default.

- Never ask for or expose an annotation resource path as a normal parameter
- Infer species only when unambiguous; otherwise ask whether the genes are maize, wheat, or rice
- Show three or four example rows when asking for a gene list
- Use default thresholds and output location unless the user requests overrides
- Do not invent paths

## Result Interpretation

After a successful run, report:

- selected species and resource
- candidate IDs represented in the PFAM background
- total and significant PFAM counts
- top domains with candidate count and adjusted p-value
- all output paths
