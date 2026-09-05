# EasyGS Analysis Container

This container packages EasyGS with its analysis environments. It is intended
for users who want to mount data and run EasyGS without installing conda,
R, PLINK, bcftools, or the EasyGS Python package on the host.

For an automated source checkout, image build, and service start, use the
repository-level `install.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | bash
```

The image builds the current EasyGS source and WebUI together with five analysis
environments:

- `EasyGS_1`: R-based GWAS, annotation, enrichment, and correlation workflows
- `EasyGS_2`: PLINK/VCF, population genetics, imputation, and extraction workflows
- `EasyGS_3`: genomic prediction and variance-decomposition workflows
- `EasyGS_4`: Fast3VmrMLM QEI workflows
- `EasyGS_5`: FASTQ quality control, alignment, and GATK variant calling

The build also validates the commands and key R packages required by these
workflows before producing the image.

## Build

```bash
cd /path/to/easygs
container/build.sh
```

The build defaults to China-friendly mirrors:

- Debian: TUNA
- Miniforge / conda: TUNA
- npm: npmmirror
- PyPI: TUNA

The default Miniforge installer is for Linux x86_64/amd64. Use a matching
`MINIFORGE_URL` build argument if you build for another architecture.

You can switch mirrors at build time:

```bash
container/build.sh analysis \
  --build-arg APT_MIRROR=http://mirrors.bfsu.edu.cn/debian \
  --build-arg APT_SECURITY_MIRROR=http://mirrors.bfsu.edu.cn/debian-security \
  --build-arg CONDA_MIRROR=https://mirrors.bfsu.edu.cn/anaconda \
  --build-arg MINIFORGE_URL=https://mirrors.bfsu.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-Linux-x86_64.sh
```

## Run

EasyGS containers require two host directories:

- `easygs-home`: mounted to `/home/easygs/.easygs`; stores `config.json`,
  workspace outputs, resources, history, and cron state.
- `data`: mounted to `/data`; stores user input datasets.

Run with Docker:

```bash
docker run --rm -it \
  --network host \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  -e EASYGS_AGENTS__DEFAULTS__MODEL=deepseek-v4-pro \
  -e EASYGS_AGENTS__DEFAULTS__MAX_TOKENS=8192 \
  -e EASYGS_AGENTS__DEFAULTS__REASONING_EFFORT=max \
  -e EASYGS_PROVIDERS__DEEPSEEK__API_KEY=sk-xxx \
  easygs:analysis
```

With Docker Compose, copy `.env.example` to `.env` and set both required
directories:

```dotenv
EASYGS_HOME_DIR=./easygs-home
EASYGS_DATA_DIR=/path/to/data
```

The same file can configure the image tag, model limits, shell timeout,
workspace restriction, Brave Search, provider credentials, notifications, and
an optional container UID/GID override.

Compose exits with an error if either variable is empty or missing.
Create both host directories before the first start so ownership is clear:

```bash
mkdir -p ./easygs-home /path/to/data
```

Open:

```text
http://127.0.0.1:25685
```

Inside EasyGS, refer to mounted input files by their container path:

```text
/data/example.vcf.gz
```

Outputs are written to EasyGS' normal workspace:

```text
/home/easygs/.easygs/workspace
```

With the compose defaults, that path maps to:

```text
container/easygs-home/workspace
```

External resources are not bundled into the image. Put resources under:

```text
container/easygs-home/resources
```

For the default maize B73 v4 FASTQ-to-VCF analysis, place the reference under:

```text
container/easygs-home/resources/fastq_to_vcf_analysis/
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.amb
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.ann
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.bwt
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.pac
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.sa
├── Zm-B73-REFERENCE-GRAMENE-4.0.fa.fai
└── Zm-B73-REFERENCE-GRAMENE-4.0.dict
```

Only the FASTA is required. Existing indexes are reused when present; missing BWA indexes,
FASTA index, and sequence dictionary are generated inside the workflow project under
`00-Reference/`. To use another diploid reference assembly, pass `reference_fasta` with a path
visible inside the container, such as `/data/reference/genome.fa`. An optional `sample_sheet`
TSV with `sample_id`, `r1`, and `r2` columns supports paired FASTQs with arbitrary filenames.

For maize/wheat/rice candidate-gene extraction, place the three species gene BED resources under:

```text
container/easygs-home/resources/candidate_gene_extraction_analysis/
```

For maize/wheat/rice genebody locus annotation, place the three real species gene BED resources
under (symbolic links are rejected):

```text
container/easygs-home/resources/genebody_locus_annotation_analysis/
```

For wheat/rice offline GO/KEGG enrichment, place the seven required mapping and
annotation files under:

```text
container/easygs-home/resources/wheat_rice_gene_function_enrichment_analysis/
```

For maize/wheat/rice peak annotation, place the species GFF3 resources under:

```text
container/easygs-home/resources/peak_annotation_analysis/
```

For maize/wheat/rice ortholog extraction, place the three species matrices under:

```text
container/easygs-home/resources/ortholog_extraction_analysis/
```

For maize/wheat/rice PFAM enrichment, place the species mapping/annotation resources under:

```text
container/easygs-home/resources/pfam_enrichment_analysis/
```

## Docker Compose

```bash
cd container
cp .env.example .env
# Edit EASYGS_HOME_DIR, EASYGS_DATA_DIR, model, and provider credentials, then:
docker compose up
```

The compose file uses `network_mode: host` because the current EasyGS WebUI
bootstrap endpoint is intentionally localhost-only.

## Commands

Run any EasyGS command by passing it after the image name:

```bash
docker run --rm -it \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis easygs status

docker run --rm -it \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis easygs agent
```

Check bundled analysis environments:

```bash
docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis conda env list

docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis mamba run -n EasyGS_1 bash -c 'command -v bcftools'

docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis mamba run -n EasyGS_2 bash -c 'command -v plink'

docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis mamba run -n EasyGS_5 bash -c \
  'for tool in fastp bwa samtools picard gatk bcftools bgzip tabix; do command -v "$tool"; done'
```
