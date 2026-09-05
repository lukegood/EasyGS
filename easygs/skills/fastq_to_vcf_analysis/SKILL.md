---
name: fastq_to_vcf_analysis
description: Run a configurable-reference diploid paired-end short-read FASTQ-to-VCF pipeline, using managed maize B73 v4 by default.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# FASTQ to VCF Skill

Use the built-in `fastq_to_vcf_analysis` tool for diploid paired-end short-read
FASTQ-to-VCF processing. It uses the managed maize B73 v4 reference by default and
accepts another uncompressed reference FASTA when requested.

Treat this as one complete workflow:

1. discover and validate all paired FASTQ samples, optionally from a sample sheet
2. prepare or reuse reference indexes in the project directory
3. run fastp quality control
4. align clean reads with BWA and process BAM files with samtools and Picard
5. call per-sample gVCFs with GATK HaplotypeCaller
6. combine only the current run's gVCFs and perform joint genotyping
7. apply configurable genotype-depth and allele-depth filters
8. export the final compressed VCF, index, statistics, genotype table, logs, and summary

Do not split these stages into separate public tools. Do not expose reference-index paths or
bundled Python helper scripts as user parameters.

## Tool-First Rule

Use `fastq_to_vcf_analysis(...)` for execution.

## Required Input

- `fastq_dir`: a directory containing one or more paired samples. Every sample must have both:

```text
<sample_id>_1.fq.gz
<sample_id>_2.fq.gz
```

The suffixes identify the two reads in each paired-end sample; they do not limit the directory to
one sample. For example, these four files represent two samples:

```text
DH09156_1.fq.gz
DH09156_2.fq.gz
DH09157_1.fq.gz
DH09157_2.fq.gz
```

Sample IDs may contain letters, numbers, `.`, `_`, and `-`.

To use other filenames, provide `sample_sheet`, a TSV containing exactly these columns:

```text
sample_id\tr1\tr2
sample01\treads/sample01_R1.fastq.gz\treads/sample01_R2.fastq.gz
```

Relative read paths are resolved relative to the sample-sheet directory.

## Optional Parameters

- `project_id`: project and result-directory name; default: the FASTQ directory name
- `sample_sheet`: TSV defining sample IDs and paired-read paths
- `reference_fasta`: uncompressed `.fa`, `.fasta`, or `.fna`; default: managed B73 v4
- `threads`: threads used by individual commands; default: `10`
- `parallel_jobs`: concurrent per-sample HaplotypeCaller jobs; default: `10`
- `platform`: SAM read-group sequencing platform; default: `DNBSEQ`
- `library`: read-group library identifier; default: `lib1`
- `min_depth`: mask genotype calls below this DP; default: `5`
- `min_allele_depth`: for heterozygotes, mask calls when a called allele has lower AD; default: `4`
- `output_dir`: parent result directory; runtime context supplies the default when omitted

## Managed Resources

By default, the tool uses the maize B73 v4 FASTA from:

```text
~/.easygs/resources/fastq_to_vcf_analysis/
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.amb
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.ann
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.bwt
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.pac
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.sa
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.fai
└── Zm-B73-REFERENCE-GRAMENE-4.0.dict
```

Only the FASTA is required. Existing sidecar indexes are reused when present. Missing BWA
indexes, `.fai`, and `.dict` are generated under `<project>/00-Reference/`, so the source
reference directory is not modified. `EASYGS_RESOURCES_DIR` may override the resource root.

For another diploid organism or assembly, pass `reference_fasta`. The pipeline does not claim
support for single-end reads, long-read data, or non-diploid genotype calling.

## Outputs

For `project_id=E250143075`, outputs are written under
`<output_dir>/E250143075/`:

```text
00-Reference/          project-local reference link and indexes
01-QC/                 fastp HTML/JSON and clean paired FASTQs
02-Mapping/            sorted/deduplicated BAM files and indexes
03-VariantCalling/     per-sample gVCFs and joint-calling intermediates
04-Output/
  E250143075.vcf.gz
  E250143075.vcf.gz.tbi
  snp_statistics.tsv
  genotypes.tsv
logs/
E250143075_summary.txt
```

## Runtime and Validation

The workflow runs in the `EasyGS_5` conda environment and requires `fastp`, `bwa`,
`samtools`, `picard`, `gatk`, `bgzip`, `tabix`, `python3`, and `xargs`.

It stops before execution when FASTQ mates are missing, sample names are invalid, the selected
reference FASTA is missing, numeric parameters are invalid, or required environment tools are
unavailable. A project directory cannot be silently reused with a different reference genome.

After a successful run, report the number of samples, project directory, QC directory, final VCF
and index, logs directory, and summary path.
