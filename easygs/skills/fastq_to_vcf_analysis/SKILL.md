---
name: fastq_to_vcf_analysis
description: Run the existing maize B73 v4 paired-end FASTQ-to-VCF pipeline for any number of matched sample pairs.
metadata: {"easygs":{"emoji":"🧬","os":["linux"]}}
---

# FASTQ to VCF Skill

Use the built-in `fastq_to_vcf_analysis` tool for the maize B73 v4 paired-end
FASTQ-to-VCF workflow.

Treat this as one complete workflow:

1. discover and validate all paired FASTQ samples
2. run fastp quality control
3. align clean reads with BWA and process BAM files with samtools and Picard
4. call per-sample gVCFs with GATK HaplotypeCaller
5. combine gVCFs and perform joint genotyping
6. apply the existing genotype filters
7. export the final compressed VCF, index, statistics, genotype table, logs, and summary

Do not split these stages into separate public tools. Do not expose the reference FASTA,
reference indexes, or bundled Python helper scripts as user parameters.

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

## Optional Parameters

- `project_id`: project and result-directory name; default: the FASTQ directory name
- `threads`: threads used by individual commands; default: `10`
- `parallel_jobs`: concurrent per-sample HaplotypeCaller jobs; default: `10`
- `output_dir`: parent result directory; runtime context supplies the default when omitted

## Managed Resources

The tool uses the maize B73 v4 FASTA and its prebuilt indexes from:

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

These must be real regular files in the resource directory. `EASYGS_RESOURCES_DIR` may override
the resource root.

## Outputs

For `project_id=E250143075`, outputs are written under
`<output_dir>/E250143075/`:

```text
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

It stops before execution when FASTQ mates are missing, sample names are invalid, managed
reference files are missing, numeric parameters are invalid, or required environment tools are
unavailable.

After a successful run, report the number of samples, project directory, QC directory, final VCF
and index, logs directory, and summary path.
