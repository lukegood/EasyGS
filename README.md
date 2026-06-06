<div align="center">
  <img src="easygs_logo_withname.png" alt="EasyGS" width="500">
  <h1>EasyGS: An AI Assistant for Crop Genomic Selection Analysis</h1>
  <p>
    <a href="README.md">
      <img src="https://img.shields.io/badge/English-1f6feb?style=for-the-badge" alt="English">
    </a>
    <a href="README_zh.md">
      <img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-e5e7eb?style=for-the-badge&amp;logoColor=black" alt="简体中文">
    </a>
  </p>
</div>

EasyGS is an AI assistant for crop genomic selection and genomic data analysis. Users describe an analysis task in natural language, and EasyGS helps check input files, collect parameters, run local analysis workflows, and summarize the outputs.

## Highlights

- Natural language analysis: submit VCF, phenotype, environment, gene annotation, and breeding analysis tasks through conversation.
- Local execution: run workflows on your own workstation or server, keeping data, environments, and outputs under your control.
- 39 built-in analysis tools: covering data QC, population structure, genetic parameter estimation, genomic prediction, environmental interaction, GWAS, and functional annotation.
- Background workflows: suitable for long-running genomic analyses.
- Multiple entry points: CLI, local WebUI, and optional messaging channels such as Feishu/Lark.

## Recommended Installation: Local

Local installation is recommended for most users who run EasyGS on a research workstation, server, or cluster login node.

### 1. Prepare Requirements

- Python 3.11 or newer
- conda or mamba
- A working LLM API key

### 2. Install EasyGS

Download the wheel package from the release page, for example:

```text
easygs-0.1.3-py3-none-any.whl
```

Install it locally:

```bash
pip install /path/to/easygs-0.1.3-py3-none-any.whl
```

Check the installation:

```bash
easygs --version
```

### 3. Install Analysis Environments

EasyGS analysis tools use several conda environments. Download the matching `env_all/` directory from the release assets, or use the `env_all/` directory from the source tree, then create the environments:

```bash
conda env create -f env_all/EasyGS_1.yml
conda env create -f env_all/EasyGS_2.yml
conda env create -f env_all/EasyGS_3.yml
conda env create -f env_all/EasyGS_4.yml
```

Skip any command for an environment that already exists.

### 4. Initialize Configuration

```bash
easygs onboard
```

This creates the default configuration and workspace:

```text
~/.easygs/config.json
~/.easygs/workspace/
~/.easygs/resources/
```

### 5. Configure Model and Workspace

Open the configuration file:

```bash
nano ~/.easygs/config.json
```

You can also use VS Code, vim, or any editor available on your server.

#### 5.1 Choose the Provider

First choose the model provider you want to use, then configure only that provider:

| If you use | Configure |
| --- | --- |
| DeepSeek | `providers.deepseek` |
| GLM / Zhipu AI | `providers.zhipu` |
| Kimi / Moonshot | `providers.moonshot` |
| MiniMax | `providers.minimax` |
| Qwen / Alibaba Cloud DashScope | `providers.dashscope` |
| Custom compatible endpoint | `providers.custom` |

Your config may contain many provider sections. Leave unused providers empty.

#### 5.2 Fill Provider Credentials

Fill both `apiKey` and `apiBase` under the provider you selected. `apiKey` is the provider credential, and `apiBase` is the API endpoint from the provider or gateway.

For DeepSeek:

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

For a custom compatible endpoint, fill `apiKey` and `apiBase` under `custom`:

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

#### 5.3 Set the Default Model

After configuring the provider, set `agents.defaults.model`. The model name should match the provider:

| Provider | Model example |
| --- | --- |
| `providers.deepseek` | `deepseek-chat` |
| `providers.zhipu` | `glm-4` |
| `providers.moonshot` | `kimi-k2.5` |
| `providers.minimax` | `MiniMax-M2.1` |
| `providers.dashscope` | `qwen-max` |
| `providers.custom` | Any model supported by your custom service |

For DeepSeek:

```json
{
  "agents": {
    "defaults": {
      "model": "deepseek-chat"
    }
  }
}
```

#### 5.4 Set the Workspace

Find `agents.defaults.workspace` and confirm that it points to the EasyGS working directory:

```json
{
  "agents": {
    "defaults": {
      "workspace": "~/.easygs/workspace"
    }
  }
}
```

The default is usually fine. Analysis outputs, intermediate files, and task records are written there.

#### 5.5 Keep Research Mode Enabled

For analysis tasks, keep Research Mode enabled:

```json
{
  "agents": {
    "defaults": {
      "researchMode": true
    }
  }
}
```

#### 5.6 Save and Check

After saving `~/.easygs/config.json`, run:

```bash
easygs status
```

If the status output says the provider is not configured, check:

- The matching `providers.<name>.apiKey` is filled.
- The matching `providers.<name>.apiBase` is filled with the complete API endpoint from the provider or gateway.
- `agents.defaults.model` uses the expected provider/model name.

You can also temporarily override configuration with environment variables:

```bash
export EASYGS_AGENTS__DEFAULTS__MODEL=deepseek-chat
export EASYGS_PROVIDERS__DEEPSEEK__API_KEY=your-api-key
```

### 6. Enable the Web UI and Start

The Web UI is the recommended default interaction mode. Enable the websocket channel in `~/.easygs/config.json`:

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

If EasyGS runs on your local machine, open:

```text
http://127.0.0.1:25685
```

If EasyGS runs on a remote server, create an SSH tunnel from your own computer first:

```bash
ssh -L 25685:127.0.0.1:25685 user@server_ip
```

Replace `user@server_ip` with your server username and address. Keep the SSH session open, then open this URL in your local browser:

```text
http://127.0.0.1:25685
```

If local port `25685` is already in use, choose another local port:

```bash
ssh -L 18080:127.0.0.1:25685 user@server_ip
```

Then open:

```text
http://127.0.0.1:18080
```

In the Web UI, submit analysis tasks with natural language. For example:

```text
Please summarize basic statistics for /data/example.vcf.gz
```

You can also use the CLI as a supplement. Run a one-shot request:

```bash
easygs agent -m "Please summarize basic statistics for /data/example.vcf.gz"
```

Start an interactive CLI session:

```bash
easygs agent
```

## Optional Installation: Docker

Use Docker if you prefer a containerized runtime.

```bash
cd /path/to/easygs
cp .env.example .env
mkdir -p ./easygs-home ./data
```

Edit `.env` with the image, model, and provider credentials, then run:

```bash
docker compose pull
docker compose up -d
```

Inside the container, refer to mounted data files with `/data/...` paths. See [container/README.md](container/README.md) for more details.

## 39 Built-in Analysis Tools

| Category | Function | Description |
| --- | --- | --- |
| Data QC | VCF statistics (`vcf_stats`) | Generate basic VCF statistics. |
| Data QC | Allele frequency analysis (`allele_frequency_analysis`) | Use vcftools to analyze allele frequency and summarize the proportion of polymorphic sites. |
| Data QC | MAF distribution analysis (`maf_distribution_analysis`) | Use PLINK to analyze minor allele frequency distribution. |
| Data QC | Missingness analysis (`missingness_analysis`) | Use PLINK to analyze site or sample missingness. |
| Data QC | Variant filtering (`variant_filter_analysis`) | Use PLINK to filter by sample missingness, variant missingness, HWE, and MAF. |
| Data QC | VCF format conversion (`vcf_format_conversion_analysis`) | Convert between VCF and PLINK BED/BIM/FAM or PED/MAP formats. |
| Data QC | Genotype encoding (`genotype_encoding_analysis`) | Use PLINK to encode additive 0/1/2 genotypes. |
| Data QC | VCF variant extraction (`vcf_variant_extract_analysis`) | Extract target subsets from VCF by variant or sample list. |
| Data QC | LD pruning analysis (`ld_prune_analysis`) | Use PLINK for LD pruning. |
| Data QC | Regional R2 analysis (`region_r2_analysis`) | Use PLINK for regional linkage disequilibrium R2 analysis. |
| Data QC | Genotype imputation (`genotype_imputation_analysis`) | Use Beagle for genotype imputation. |
| Population genetic structure | Nucleotide diversity analysis (`nucleotide_diversity_analysis`) | Use vcftools to calculate site-level or window-based nucleotide diversity pi. |
| Population genetic structure | PCA analysis (`pca_analysis`) | Use PLINK for principal component analysis. |
| Population genetic structure | ADMIXTURE analysis (`admixture_analysis`) | Use ADMIXTURE for population structure analysis and best-K selection. |
| Population genetic structure | Genomic relationship matrix (`grm_analysis`) | Use GCTA to construct a genomic relationship matrix. |
| Population genetic structure | LD decay analysis (`ld_decay_analysis`) | Use PopLDdecay for linkage disequilibrium decay analysis. |
| Genetic parameter estimation and genomic prediction | Heritability estimation (`heritability`) | Use GCTA to calculate single-trait heritability. |
| Genetic parameter estimation and genomic prediction | Variance decomposition (`variance_decomposition_analysis`) | Use linear models to decompose phenotypic variance into genotype, environment, and residual components. |
| Genetic parameter estimation and genomic prediction | Phenotype BLUP analysis (`phenotype_blup_analysis`) | Calculate BLUP values from multi-environment phenotype data. |
| Genetic parameter estimation and genomic prediction | Combining ability analysis (`combining_ability_analysis`) | Estimate parental GCA and hybrid SCA. |
| Genetic parameter estimation and genomic prediction | GEBV estimation (`gebv_analysis`) | Use GCTA to estimate genomic estimated breeding values. |
| Genetic parameter estimation and genomic prediction | rrBLUP genomic prediction (`rrblup_prediction_analysis`) | Use rrBLUP for genomic prediction. |
| Genetic parameter estimation and genomic prediction | VCF genomic prediction matrix (`vcf_genomic_prediction_csv_analysis`) | Generate a 0/1/2 genotype CSV matrix from VCF. |
| Genetic parameter estimation and genomic prediction | Cross-validation grouping (`cvf_split_analysis`) | Generate cross-validation grouping CSV files from material lists. |
| Environment and phenotype parsing | Environmental-factor correlation analysis (`env_factor_correlation_analysis`) | Calculate Pearson correlations among environmental factors in the same region and draw a heatmap. |
| Environment and phenotype parsing | Cross-region phenotypic correlation analysis (`cross_region_phenotypic_correlation_analysis`) | Calculate Pearson correlations for the same phenotype across regions and draw a heatmap. |
| Environment and phenotype parsing | Environment index analysis (`environment_index_analysis`) | Run environment index analysis based on the CERIS framework. |
| Environment and phenotype parsing | Reaction norm analysis (`reaction_norm_analysis`) | Convert multi-environment phenotype data to long format and calculate reaction norm intercepts and slopes. |
| Environment and phenotype parsing | Genotype-by-environment analysis (`GxE_analysis`) | Run SNP x environmental factor ANOVA from VCF, environmental factors, and phenotype data. |
| Gene mining and functional interpretation | GWAS analysis | Use three rMVP algorithms for genome-wide association analysis. |
| Gene mining and functional interpretation | QEI detection analysis (`QEI_detection_analysis`) | Use Fast3VmrMLM for multi-environment QEI detection. |
| Gene mining and functional interpretation | Genotype-by-genotype analysis (`GxG_analysis`) | Run SNP x SNP ANOVA from VCF and phenotype data. |
| Gene mining and functional interpretation | Gene extraction (`gene_extraction_analysis`) | Expand significant-locus windows and annotate candidate genes in the intervals. |
| Gene mining and functional interpretation | Gene function annotation (`gene_function_annotation_analysis`) | Run maize gene GO and KEGG functional enrichment analysis. |
| Gene mining and functional interpretation | Protein domain annotation (`protein_function_annotation_analysis`) | Use InterProScan for maize protein domain annotation. |
| Gene mining and functional interpretation | Maize PFAM domain enrichment (`pfam_enrichment_analysis`) | Run maize protein domain enrichment analysis. |
| Gene mining and functional interpretation | Maize locus structure annotation (`strcture_annotation_analysis`) | Use ChIPseeker for locus structure annotation. |
| Gene mining and functional interpretation | Maize gene-body locus annotation (`genebody_locus_annotation_analysis`) | Annotate SNPs located in gene regions of the maize B73 V4 reference genome. |
| Gene mining and functional interpretation | Ortholog extraction (`ortholog_extraction_analysis`) | Extract maize ortholog gene sets in other species. |

## Common Commands

| Command | Purpose |
| --- | --- |
| `easygs onboard` | Initialize configuration and workspace files. |
| `easygs agent` | Start a CLI chat session. |
| `easygs gateway` | Start the WebUI or messaging gateway. |
| `easygs status` | Show configuration, workspace, resources, and model status. |
| `easygs workflows list` | List background analysis tasks. |
| `easygs workflows status <workflow_id>` | Show the status of a workflow. |
| `easygs workflows result <workflow_id>` | Show workflow results. |

## External Resources

Some tools require large reference files that are not bundled with EasyGS. The default resource directory is:

```text
~/.easygs/resources/
```

For example, protein function annotation and PFAM enrichment require:

```text
~/.easygs/resources/pfam_enrichment_analysis/all_maize_longest_cds.txt
~/.easygs/resources/pfam_enrichment_analysis/all_maize_genes_proteins.fa.tsv
```

If a resource is missing, EasyGS reports the exact missing path at runtime.

## Messaging Channels

EasyGS supports the CLI, local WebUI, and multiple messaging channels. After enabling a channel, start the service with `easygs gateway`.

| Channel | Config section |
| --- | --- |
| WebUI / WebSocket | `channels.websocket` |
| [Feishu / Lark](docs/feishu.md) | `channels.feishu` |
| Telegram | `channels.telegram` |
| DingTalk | `channels.dingtalk` |
| Discord | `channels.discord` |
| Email | `channels.email` |
| Slack | `channels.slack` |
| QQ | `channels.qq` |
| WhatsApp | `channels.whatsapp` |
| Mochat | `channels.mochat` |

## License

EasyGS is released under the MIT License.

## Acknowledgement

This project was inspired by [nanobot](https://github.com/HKUDS/nanobot) from [HKUDS](https://github.com/HKUDS). We sincerely thank the original authors for their open-source contribution.
