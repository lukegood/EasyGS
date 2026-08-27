<div align="center">
  <img src="easygs_logo_withname.png" alt="EasyGS" width="500">
  <h1>EasyGS: An Easy-to-Use AI Agent for Natural Language-Driven Crop Genomic Selection Analysis</h1>
  <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/lukegood/EasyGS">
  <img alt="GitHub forks" src="https://img.shields.io/github/forks/lukegood/EasyGS">
  <img alt="GitHub License" src="https://img.shields.io/github/license/lukegood/EasyGS">
  <p>
    <a href="README.md">
      <img src="https://img.shields.io/badge/English-1f6feb?style=for-the-badge" alt="English">
    </a>
    <a href="README_zh.md">
      <img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-e5e7eb?style=for-the-badge&amp;logoColor=black" alt="简体中文">
    </a>
  </p>
</div>

EasyGS is an AI agent for crop genomic selection analysis. Users can describe their analysis needs in natural language, and EasyGS helps check input files, complete parameters, call human-verified GS analysis workflows, and organize output results, helping you complete GS analysis tasks.

## :raised_hands: Why EasyGS?

- **Professional GS analysis capabilities**: 51 built-in analysis workflows covering FASTQ-to-VCF processing, data QC, population structure, genetic parameter estimation, genomic prediction, environmental interaction, GWAS, and functional annotation for maize, wheat, and rice.
- **Natural-language driven**: submit analysis tasks involving VCF files, phenotype data, environmental factors, gene annotation, and more through conversation without manually writing code.
- **Long tasks run in the background**: tasks execute in the background, so you do not need to worry about interruptions.
- **Fully traceable**: check analysis progress at any time, keep intermediate results for every step, and review the workflow whenever needed.
- **Flexible usage**: use EasyGS through the Web UI, command line, Telegram, Feishu/Lark, and other messaging channels, so you can choose the workflow that suits you.

## :earth_asia: Interface Preview

<table>
  <tr>
    <td align="center" valign="top" width="55%">
      <h3>Web UI</h3>
      <p>Chat with EasyGS in your browser, simply and efficiently</p>
      </br>
      </br>
      <img src="pics/EasyGS_UI.png" alt="EasyGS local Web UI" height="260">
    </td>
    <td align="center" valign="top" width="45%">
      <h3>Multiple Chat Integrations</h3>
      <p>Use EasyGS through Telegram, Feishu/Lark, and other messaging channels, including on mobile devices</p>
      <img src="pics/feishuui.png" alt="EasyGS Feishu messaging interface" height="260">
    </td>
  </tr>
</table>

## :tada: Feature Preview

<table>
  <tr>
    <td align="center" valign="top" width="60%">
      <h3>Real-Time Workflow Query</h3>
      <p>Check the status, progress, and results of background analysis tasks at any time</p>
      <img src="pics/gzlxq.png" alt="EasyGS real-time workflow query" height="380">
    </td>
    <td align="center" valign="top" width="40%">
      <h3>Fully Traceable Process</h3>
      <p>Keep analysis steps and intermediate results for easy workflow review</p>
      <img src="pics/bzzz.png" alt="EasyGS fully traceable process" height="380">
    </td>
  </tr>
</table>

<div align="center">
  <h3>Diverse GS Analysis Tools</h3>
  <p>Covering common workflows such as data QC, genomic prediction, GWAS, environmental interaction, correlation analysis, functional annotation, and more...</p>
  <table>
    <tr>
      <td align="center" valign="top" width="50%">
        <img src="pics/gwas.jpg" alt="EasyGS GS analysis result example" height="400">
      </td>
      <td align="center" valign="top" width="50%">
        <img src="pics/bxxgx.png" alt="EasyGS GS analysis result example" height="400">
      </td>
    </tr>
  </table>
</div>

<p align="center"><strong>More tools are waiting for you to explore...</strong></p>

## :raising_hand: Installation

> [!WARNING]
> EasyGS is an AI Agent that can execute analysis tasks and may create, modify, or delete files. Use it in a test or dedicated working directory, and back up important data in advance. Direct production use is not recommended.

The one-command Docker installer described below is recommended for most users. The native installation steps in this section remain available for developers and users who prefer to manage Python, conda, and analysis dependencies themselves.

### 1. Requirements

- Python 3.11 or newer
- conda or mamba
- An available LLM API key

### 2. Install EasyGS

Install the latest released wheel directly from GitHub:

```bash
pip install https://github.com/lukegood/EasyGS/releases/download/v0.1.8/easygs-0.1.8-py3-none-any.whl
```

You can also open the release page and download the wheel manually:

- Latest release: <https://github.com/lukegood/EasyGS/releases/latest>
- Current wheel: <https://github.com/lukegood/EasyGS/releases/download/v0.1.8/easygs-0.1.8-py3-none-any.whl>

After downloading the file, install it with:

```bash
pip install /path/to/easygs-0.1.8-py3-none-any.whl
```

Confirm that the installation succeeded:

```bash
easygs --version
```

### 3. Install Analysis Dependencies

EasyGS analysis tools depend on several conda environments. Download the source code from the release page, or clone the repository, then use the `env_all/` directory to create the environments:

```bash
git clone https://github.com/lukegood/EasyGS.git
cd EasyGS
```

```bash
conda env create -f env_all/EasyGS_1.yml
conda env create -f env_all/EasyGS_2.yml
conda env create -f env_all/EasyGS_3.yml
conda env create -f env_all/EasyGS_4.yml
conda env create -f env_all/EasyGS_5.yml
```

If an environment already exists, you can skip the corresponding command. `EasyGS_5` provides the fastp, BWA, samtools, Picard, GATK, bcftools, bgzip, and tabix dependencies used by `fastq_to_vcf_analysis`.

### 4. Initialize Configuration

```bash
easygs onboard
```

This command creates the default configuration file and workspace:

```text
~/.easygs/config.json
~/.easygs/workspace/
~/.easygs/resources/
```

### 5. Configure the Model and Workspace

Open the configuration file:

```bash
nano ~/.easygs/config.json
```

You can also use your preferred editor, such as VS Code, vim, or a text editor available on your server.

#### 5.1 Configure the LLM Provider

First decide which model provider you want to use, then configure only that provider. Common provider names include:

| If you use | Configure this item |
| --- | --- |
| DeepSeek | `providers.deepseek` |
| GLM / Zhipu AI | `providers.zhipu` |
| Kimi / Moonshot | `providers.moonshot` |
| MiniMax | `providers.minimax` |
| Qwen / Alibaba Cloud DashScope | `providers.dashscope` |
| Custom compatible endpoint | `providers.custom` |

Your configuration file may already contain multiple provider sections. Providers you do not use can be left empty.

#### 5.2 Fill Provider Credentials

Under the provider you selected, fill in `apiKey` and `apiBase`. `apiKey` is the provider key, and `apiBase` is the API address provided by the provider or gateway.

For example, when using DeepSeek:

```json
{
  "providers": {
    "deepseek": {
      "apiKey": "your-api-key",
      "apiBase": "your-api-base"
    }
  }
}
```

If you use a custom compatible endpoint, fill in `apiKey` and `apiBase` under `custom` in the same way:

```json
{
  "providers": {
    "custom": {
      "apiKey": "your-api-key",
      "apiBase": "https://your-api-base/v1"
    }
  }
}
```

#### 5.3 Configure the Default Model

After configuring the provider, set `agents.defaults.model`. The model name should match the provider:

| Provider | Model name example |
| --- | --- |
| `providers.deepseek` | `deepseek-v4-pro` |
| `providers.zhipu` | `glm-5.1` |
| `providers.moonshot` | `kimi-k2.6` |
| `providers.minimax` | `MiniMax-M2.7` |
| `providers.dashscope` | `qwen-3.6-plus` |
| `providers.custom` | A model name supported by your custom service |

For example, when using DeepSeek V4 Pro, set the model, generation limit, and reasoning effort together:

```json
{
  "agents": {
    "defaults": {
      "model": "deepseek-v4-pro",
      "maxTokens": 384000,
      "reasoningEffort": "max"
    }
  }
}
```

`maxTokens` controls the maximum generation length for a single response, and `reasoningEffort` sets the reasoning intensity for DeepSeek V4 Pro. DeepSeek V4 models support up to 1M context and up to 384000 output tokens on the model side. EasyGS does not expose a `contextWindow` control; it passes the current conversation, tool results, and analysis context to the selected model.

#### 5.4 Save and Check the Configuration

After saving `~/.easygs/config.json`, run:

```bash
easygs status
```

If the status output says the provider is not configured, check:

- Whether the corresponding `providers.<name>.apiKey` has been filled in.
- Whether the corresponding `providers.<name>.apiBase` has been filled with the complete API address provided by the provider or gateway.
- Whether `agents.defaults.model` is set to the model name for the corresponding provider.

### 6. Enable the Web UI and Start Using EasyGS

The Web UI is recommended as the default interaction mode. First enable websocket in `~/.easygs/config.json`:

```json
{
  "channels": {
    "websocket": {
      "enabled": true,
      "port": 25685
    }
  }
}
```

Start the service:

```bash
easygs gateway
```

If EasyGS runs on your local machine, open this directly in your browser:

```text
http://127.0.0.1:25685
```

If EasyGS runs on a remote server, first create an SSH port forward from your own computer:

```bash
ssh -L 25685:127.0.0.1:25685 user@server_ip
```

Replace `user@server_ip` with your server login username and address. Keep this SSH connection open, then open this URL in your own computer's browser:

```text
http://127.0.0.1:25685
```

If local port `25685` is already in use, choose another local port, for example:

```bash
ssh -L 18080:127.0.0.1:25685 user@server_ip
```

Then open:

```text
http://127.0.0.1:18080
```

After entering the Web UI, you can directly submit analysis tasks in natural language. For example:

```text
Please check the basic statistics for /data/example.vcf.gz
```

You can also use the command line as a supplement. For a one-shot request:

```bash
easygs agent -m "Please check the basic statistics for /data/example.vcf.gz"
```

For an interactive command-line conversation:

```bash
easygs agent
```

## :whale: Using Docker

Docker is the recommended way to run EasyGS because the image packages EasyGS together with all five analysis environments. Users only need to mount a persistent EasyGS home directory and a data directory.

Requirements:

- Linux x86_64 with Bash and curl
- Git, Docker Engine, and Docker Compose
- A working LLM provider and API key

### One-command installation

The repository-level installer checks host dependencies, clones or updates EasyGS, interactively configures the model provider, builds the image, and starts the service:

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | bash
```

The default installation directory is `~/easygs`. To select the install directory, data directory, or Git ref:

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
  bash -s -- --install-dir "$HOME/apps/easygs" --data-dir "$HOME/easygs-data" --ref master
```

After a public image is published, the same installer can skip the local build:

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
  bash -s -- --image <registry>/<namespace>/easygs:analysis
```

For unattended servers or CI, use `--non-interactive`. To also allow installation of missing host dependencies:

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
  bash -s -- --install-deps --non-interactive
```

The installer stores deployment settings in `~/easygs/.env`. Running it again updates the source and container while preserving model, API key, Feishu/Lark, and email settings. It does not silently install missing host dependencies, and all Mamba, R, and bioinformatics dependencies remain inside the image.

### Manual Docker Compose setup

The root-level `docker-compose.yml` pulls the image named by `EASYGS_IMAGE`:

```bash
cd /path/to/easygs
cp .env.example .env
mkdir -p ./easygs-home ./data
```

Edit `.env` and fill in the image, model, and provider credentials. When using DeepSeek V4 Pro, you can use:

```dotenv
EASYGS_MODEL=deepseek-v4-pro
EASYGS_MAX_TOKENS=384000
EASYGS_REASONING_EFFORT=max
```

Then start:

```bash
docker compose pull
docker compose up -d
```

To build locally instead, use `container/docker-compose.yml`:

```bash
cd /path/to/easygs/container
cp .env.example .env
mkdir -p ./easygs-home /path/to/data
# Set EASYGS_HOME_DIR, EASYGS_DATA_DIR, model, and provider credentials.
docker compose build
docker compose up -d
```

Make sure `EASYGS_IMAGE`, `EASYGS_MODEL`, and the credentials for your selected provider are configured. `EASYGS_MAX_TOKENS` and `EASYGS_REASONING_EFFORT` map to the default EasyGS agent configuration. Inside the container, use `/data/...` paths to refer to mounted data files. External reference resources are not bundled in the image; place them under the mounted `easygs-home/resources/` directory. For more details, see [container/README.md](container/README.md).

## :clap: 51 GS Analysis Tools

| Category | Function | Description |
| --- | --- | --- |
| Data QC | FASTQ-to-VCF (`fastq_to_vcf_analysis`) | Process any number of matched maize paired-end FASTQ samples into a jointly called VCF using the managed B73 v4 reference. |
| Data QC | VCF statistics (`vcf_stats`) | Generate basic VCF statistics. |
| Data QC | General VCFtools operations (`vcftools_analysis`) | Run structured VCFtools operations that are not covered by a more specific EasyGS workflow. |
| Data QC | Allele frequency analysis (`allele_frequency_analysis`) | Use vcftools to analyze allele frequency and summarize the proportion of polymorphic sites. |
| Data QC | MAF distribution analysis (`maf_distribution_analysis`) | Use PLINK to analyze minor allele frequency distribution. |
| Data QC | Missingness analysis (`missingness_analysis`) | Use PLINK to analyze site or sample missingness. |
| Data QC | Variant filtering (`variant_filter_analysis`) | Use PLINK to filter by sample missingness, variant missingness, HWE, and MAF. |
| Data QC | VCF format conversion (`vcf_format_conversion_analysis`) | Convert between VCF and PLINK BED/BIM/FAM or PED/MAP formats. |
| Data QC | Genotype encoding (`genotype_encoding_analysis`) | Use PLINK to encode additive 0/1/2 genotypes. |
| Data QC | VCF variant extraction (`vcf_variant_extract_analysis`) | Extract target subsets from VCF by variant or sample list. |
| Data QC | PLINK BFILE extraction (`bfile_extract_analysis`) | Extract variants from a PLINK BED/BIM/FAM dataset into a new dataset. |
| Data QC | Sample subset extraction (`sample_subset_analysis`) | Keep or remove specified samples and export the resulting dataset. |
| Data QC | Locus subset extraction (`locus_subset_analysis`) | Keep or remove specified loci and export the resulting dataset. |
| Data QC | LD pruning analysis (`ld_prune_analysis`) | Use PLINK for LD pruning. |
| Data QC | Regional R2 analysis (`region_r2_analysis`) | Use PLINK for regional linkage disequilibrium R2 analysis. |
| Data QC | Genotype imputation (`genotype_imputation_analysis`) | Use Beagle for genotype imputation. |
| Population genetic structure | Allele count analysis (`allele_count_analysis`) | Count alleles and summarize the number of polymorphic sites. |
| Population genetic structure | Allele frequency spectrum (`allele_frequency_spectrum_analysis`) | Calculate and summarize the allele frequency spectrum. |
| Population genetic structure | Nucleotide diversity analysis (`nucleotide_diversity_analysis`) | Use vcftools to calculate site-level or window-based nucleotide diversity pi. |
| Population genetic structure | Mean nucleotide diversity (`mean_nucleotide_diversity_analysis`) | Calculate mean nucleotide diversity from a `.sites.pi` file. |
| Population genetic structure | Tajima's D (`tajima_d_analysis`) | Calculate Tajima's D in genomic windows. |
| Population genetic structure | PCA analysis (`pca_analysis`) | Use PLINK for principal component analysis. |
| Population genetic structure | ADMIXTURE analysis (`admixture_analysis`) | Use ADMIXTURE for population structure analysis and automatically determine the best K value. |
| Population genetic structure | Genomic relationship matrix GRM (`grm_analysis`) | Use GCTA to construct a genomic relationship matrix. |
| Population genetic structure | LD decay analysis (`ld_decay_analysis`) | Use PopLDdecay for linkage disequilibrium decay analysis. |
| Population genetic structure | Population structure and kinship (`population_structure_kinship_analysis`) | Run LD pruning, PCA, GRM construction, and ADMIXTURE as one workflow. |
| Genetic parameter estimation and genomic prediction | Heritability estimation (`heritability`) | Use GCTA to calculate single-trait heritability. |
| Genetic parameter estimation and genomic prediction | Variance decomposition (`variance_decomposition_analysis`) | Use linear models to decompose phenotypic variance into genotype, environment, and residual components. |
| Genetic parameter estimation and genomic prediction | Phenotype BLUP analysis (`phenotype_blup_analysis`) | Calculate BLUP values from multi-environment phenotype data. |
| Genetic parameter estimation and genomic prediction | Combining ability analysis (`combining_ability_analysis`) | Estimate parental GCA and hybrid SCA. |
| Genetic parameter estimation and genomic prediction | GEBV estimation (`gebv_analysis`) | Use GCTA to estimate genomic estimated breeding values. |
| Genetic parameter estimation and genomic prediction | rrBLUP genomic prediction (`rrblup_prediction_analysis`) | Use rrBLUP for genomic prediction. |
| Genetic parameter estimation and genomic prediction | VCF genomic prediction matrix (`vcf_genomic_prediction_csv_analysis`) | Generate a 0/1/2 genotype CSV matrix from VCF. |
| Genetic parameter estimation and genomic prediction | Cross-validation grouping (`cvf_split_analysis`) | Generate cross-validation grouping CSV files from material lists. |
| Environment and phenotype parsing | Environmental-factor correlation analysis (`env_factor_correlation_analysis`) | Calculate Pearson correlations among different environmental factors in the same region and draw a heatmap. |
| Environment and phenotype parsing | Cross-region phenotypic correlation analysis (`phenotype_region_correlation_analysis`) | Calculate Pearson correlations for the same phenotype across different regions and draw a heatmap. |
| Environment and phenotype parsing | Cross-region environmental correlation analysis (`env_region_correlation_analysis`) | Calculate correlations for environmental factors across regions and draw a heatmap. |
| Environment and phenotype parsing | Environment index analysis (`environment_index_analysis`) | Run environment index analysis based on the CERIS framework. |
| Environment and phenotype parsing | Reaction norm analysis (`reaction_norm_analysis`) | Convert multi-environment phenotype data to long format and calculate reaction norm intercepts and slopes. |
| Environment and phenotype parsing | Genotype-by-environment GxE analysis (`gene_environment_interaction_analysis`) | Run SNP x environmental factor ANOVA from VCF, environmental factors, and phenotype data. |
| Gene mining and functional interpretation | GWAS analysis (`gwas_analysis`) | Use rMVP methods for genome-wide association analysis. |
| Gene mining and functional interpretation | QEI detection analysis (`qei_detection_analysis`) | Use Fast3VmrMLM for multi-environment QEI detection. |
| Gene mining and functional interpretation | Genotype-by-genotype GxG analysis (`locus_locus_interaction_analysis`) | Run SNP x SNP ANOVA from VCF and phenotype data. |
| Gene mining and functional interpretation | Candidate gene extraction (`candidate_gene_extraction_analysis`) | Expand significant-locus windows and extract overlapping candidate genes for maize, wheat, or rice. |
| Gene mining and functional interpretation | Gene function annotation (`gene_function_annotation_analysis`) | Run maize gene GO and KEGG functional enrichment analysis. |
| Gene mining and functional interpretation | Wheat/rice GO and KEGG enrichment (`wheat_rice_gene_function_enrichment_analysis`) | Run offline GO or KEGG enrichment for wheat or rice using user-managed species databases. |
| Gene mining and functional interpretation | Protein domain annotation (`protein_function_annotation_analysis`) | Use InterProScan for maize protein domain annotation. |
| Gene mining and functional interpretation | PFAM domain enrichment (`pfam_enrichment_analysis`) | Run streaming protein-domain enrichment for maize, wheat, or rice. |
| Gene mining and functional interpretation | Locus structure annotation (`peak_annotation_analysis`) | Use species-specific GFF3 resources to annotate maize, wheat, or rice BED intervals. |
| Gene mining and functional interpretation | Maize gene-body locus annotation (`genebody_locus_annotation_analysis`) | Annotate SNPs located in gene regions of the maize B73 V4 reference genome. |
| Gene mining and functional interpretation | Ortholog extraction (`ortholog_extraction_analysis`) | Extract ortholog records from maize, wheat, or rice species matrices. |

## :bell: Common Commands

| Command | Purpose |
| --- | --- |
| `easygs onboard` | Initialize configuration and workspace. |
| `easygs agent` | Start a command-line conversation. |
| `easygs gateway` | Start the Web UI or messaging-channel service. |
| `easygs status` | View configuration, workspace, resources, and model status. |
| `easygs workflows list` | View background analysis tasks. |
| `easygs workflows status <workflow_id>` | View the status of a specified task. |
| `easygs workflows result <workflow_id>` | View task results. |

## :violin: Research Mode and Analysis Workflows

EasyGS distinguishes between regular chat usage and analysis-oriented usage. Research mode is enabled by default for scientific workflows so that results from repeated analyses do not interfere with one another.

A typical analysis workflow proceeds as follows:

1. The user provides the request, file paths, and key parameters.
2. EasyGS checks required files, managed resources, environments, and tools.
3. Long-running analysis is submitted as a background agentic workflow.
4. Each actual tool invocation is recorded as an action, and outputs are written to the target directory.
5. EasyGS generates a summary for result delivery; workflow status and results can be queried later.

Unless the user explicitly sets `output_dir`, background outputs are stored under a path such as:

```text
~/.easygs/workflows/runs/<workflow_id>/actions/<action_id>
```

## :computer: External Resources

Some workflows require large reference files that are not packaged with EasyGS. The default resource directory is:

```text
~/.easygs/resources/
```

Set `EASYGS_RESOURCES_DIR` to use a different resource root. Resource paths are resolved internally rather than exposed as normal tool parameters.

### FASTQ-to-VCF

Place the maize B73 v4 reference and indexes under:

```text
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa.amb
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa.ann
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa.bwt
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa.pac
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa.sa
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.fa.fai
~/.easygs/resources/fastq_to_vcf_analysis/Zm-B73-REFERENCE-GRAMENE-4.0.dict
```

The input directory may contain any number of matched `<sample_id>_1.fq.gz` and `<sample_id>_2.fq.gz` pairs. Outputs retain the `01-QC`, `02-Mapping`, `03-VariantCalling`, `04-Output`, and `logs` layout.

### Candidate-gene extraction

```text
~/.easygs/resources/candidate_gene_extraction_analysis/allV4gene.bed
~/.easygs/resources/candidate_gene_extraction_analysis/allwheatgene.bed
~/.easygs/resources/candidate_gene_extraction_analysis/allricegene.bed
```

The tool selects the correct gene BED from `species=maize/wheat/rice` and produces an expanded BED, a sorted unique gene list, detailed locus-to-gene matches, and a summary.

### Protein annotation and PFAM enrichment

```text
~/.easygs/resources/pfam_enrichment_analysis/all_maize_longest_cds.txt
~/.easygs/resources/pfam_enrichment_analysis/all_maize_genes_proteins.fa.tsv
~/.easygs/resources/pfam_enrichment_analysis/wheat_interpro.tsv
~/.easygs/resources/pfam_enrichment_analysis/Osativa_323_v7.0.protein_primaryTranscriptOnly.fa.tsv
```

Protein function annotation remains maize-only. PFAM enrichment supports maize, wheat, and rice; multi-gigabyte wheat/rice annotation files are processed as streams.

### Peak annotation

```text
~/.easygs/resources/peak_annotation_analysis/Zea_mays.B73_RefGen_v4.43_modify.gff3
~/.easygs/resources/peak_annotation_analysis/Taestivumcv_ChineseSpring_725_v2.1.gene.gff3
~/.easygs/resources/peak_annotation_analysis/Osativa_323_v7.0.gene.gff3
```

The tool selects the matching GFF3 for `species=maize/wheat/rice` and validates BED/GFF3 chromosome naming before execution.

### Ortholog extraction

```text
~/.easygs/resources/ortholog_extraction_analysis/maize_ortholog_matrix.tsv
~/.easygs/resources/ortholog_extraction_analysis/wheat_ortholog_matrix.tsv
~/.easygs/resources/ortholog_extraction_analysis/rice_ortholog_matrix.tsv
```

The selected matrix is matched by exact gene ID in its first column.

### Wheat/rice GO and KEGG enrichment

```text
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/wheat_gene_KO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/rice_gene_KO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/taes_KEGG_annotation.txt
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/rice_KEGG_annotation.txt
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/wheat_gene_GO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/rice_gene_GO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/GO_term_table_2026.7.16.tsv
```

The enrichment workflow asks only for a gene list and species, then selects the matching mappings and annotation database automatically. If any resource is missing, EasyGS reports the exact expected path before execution.

## :telephone_receiver: Messaging Channels

EasyGS supports the command line, local Web UI, and multiple messaging channels. After enabling a channel, use `easygs gateway` to start the service.

| Channel | Configuration item |
| --- | --- |
| Web UI | `channels.websocket` |
| [Feishu / Lark](docs/feishu.md) | `channels.feishu` |
| Telegram | `channels.telegram` |
| DingTalk | `channels.dingtalk` |
| Discord | `channels.discord` |
| Email | `channels.email` |
| Slack | `channels.slack` |
| QQ | `channels.qq` |
| WhatsApp | `channels.whatsapp` |
| Mochat | `channels.mochat` |

## :headphones: Extending EasyGS

EasyGS is designed to be extended through tools, agentic workflows, and skills. Adding a new analysis capability usually involves:

1. Adding the tool implementation under `easygs/agent/tools`.
2. Implementing `prepare_run()` and `to_metadata()` for workflow action execution.
3. Registering the workflow action in `easygs/agent/workflows.py`.
4. Adding a skill under `easygs/skills` when the agent needs domain-specific guidance.

See [Adding a Skill and Tool](docs/adding_skill_and_tool.md) for the project conventions and validation procedure.

## :loudspeaker: License

EasyGS is released under the MIT License.

## :gift_heart: Acknowledgement

This project references the [nanobot](https://github.com/HKUDS/nanobot) open-source project from [HKUDS](https://github.com/HKUDS). We thank the original authors for their open-source contribution.
