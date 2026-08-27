<div align="center">
  <img src="easygs_logo_withname.png" alt="easygs" width="500">
  <h1>EasyGS：面向基因组选择的 AI 研究助手</h1>
  <p>
    <a href="README.md">
      <img src="https://img.shields.io/badge/English-e5e7eb?style=for-the-badge&amp;logoColor=black" alt="English">
    </a>
    <a href="README_zh.md">
      <img src="https://img.shields.io/badge/%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-1f6feb?style=for-the-badge" alt="简体中文">
    </a>
  </p>
</div>

EasyGS 是一个面向基因组选择与基因组数据分析的轻量级 LLM Agent 框架。它把对话式智能体、后台任务执行、显式文件输入工作流和多渠道消息接入结合起来，让研究人员可以通过自然语言驱动本地基因组育种分析流程。

<div align="center">
  <img src="easygs_arch.png" alt="EasyGS architecture" width="1100">
</div>

## EasyGS 能做什么 :sunny:

EasyGS 面向科研和育种应用场景，既提供：

- 用于提问、补充参数、整理结果的交互式助手
- 也提供真正执行本地脚本和命令行流程的可复用分析工具

项目内置了多类分析工作流，例如：

- 变异质控、过滤、格式转换与子集提取
- 等位基因频率、MAF、LD、Tajima's D、核苷酸多样性、PCA、GRM、ADMIXTURE
- 环境因子相关性、表型相关性、BLUP、反应范式、方差分解
- GEBV 估计、rrBLUP 预测、配合力分析、GWAS、QEI 检测
- 候选基因提取、GO/KEGG 富集、蛋白功能注释、PFAM 富集、同源基因提取、位点结构注释

EasyGS 的详细能力如下：

| 类别 | 能力 | 说明 |
| --- | --- | --- |
| 变异质控与数据准备 | `fastq_to_vcf_analysis` | 使用托管的玉米 B73 v4 参考基因组，将任意数量的成对 FASTQ 样本处理为联合分型 VCF。 |
| 变异质控与数据准备 | `vcf_stats` | 生成 VCF 基础统计信息与摘要。 |
| 变异质控与数据准备 | `vcf_variant_extract_analysis` | 使用 bcftools 按位点 ID 列表提取子集 VCF。 |
| 变异质控与数据准备 | `vcf_format_conversion_analysis` | 在 VCF、PED/MAP、BED/BIM/FAM 等格式之间转换。 |
| 变异质控与数据准备 | `missingness_analysis` | 进行缺失率分析并输出报告。 |
| 变异质控与数据准备 | `variant_filter_analysis` | 执行 PLINK 变异过滤并导出过滤结果。 |
| 变异质控与数据准备 | `sample_subset_analysis` | 按样本保留或移除并导出子集数据。 |
| 变异质控与数据准备 | `locus_subset_analysis` | 按位点保留或移除并导出子集数据。 |
| 变异质控与数据准备 | `bfile_extract_analysis` | 从 PLINK BFILE 中提取变异生成新数据集。 |
| 变异质控与数据准备 | `genotype_imputation_analysis` | 基于 Beagle 执行基因型填充。 |
| 群体遗传与群体结构 | `allele_count_analysis` | 统计等位基因计数和多态位点数量。 |
| 群体遗传与群体结构 | `allele_frequency_analysis` | 计算等位基因频率并汇总多态位点比例。 |
| 群体遗传与群体结构 | `allele_frequency_spectrum_analysis` | 进行等位基因频谱分析。 |
| 群体遗传与群体结构 | `maf_distribution_analysis` | 统计 MAF 分布。 |
| 群体遗传与群体结构 | `ld_prune_analysis` | 执行 LD 剪枝。 |
| 群体遗传与群体结构 | `ld_decay_analysis` | 进行 LD 衰减分析。 |
| 群体遗传与群体结构 | `region_r2_analysis` | 计算指定基因组区域内的位点 R²。 |
| 群体遗传与群体结构 | `tajima_d_analysis` | 计算 Tajima's D。 |
| 群体遗传与群体结构 | `nucleotide_diversity_analysis` | 执行位点或窗口核苷酸多样性分析。 |
| 群体遗传与群体结构 | `mean_nucleotide_diversity_analysis` | 从 `.sites.pi` 文件计算平均 pi。 |
| 群体遗传与群体结构 | `pca_analysis` | 执行 PCA 并生成解释方差报告。 |
| 群体遗传与群体结构 | `grm_analysis` | 构建基因组关系矩阵（GRM）。 |
| 群体遗传与群体结构 | `admixture_analysis` | 执行 ADMIXTURE 群体结构分析。 |
| 群体遗传与群体结构 | `population_structure_kinship_analysis` | 联合执行 LD 剪枝、PCA、GRM 和 ADMIXTURE。 |
| 表型、环境与互作分析 | `phenotype_blup_analysis` | 基于多环境表型数据计算 BLUP。 |
| 表型、环境与互作分析 | `phenotype_region_correlation_analysis` | 计算跨地区表型相关性并绘制热图。 |
| 表型、环境与互作分析 | `env_factor_correlation_analysis` | 计算环境因子相关性并绘制热图。 |
| 表型、环境与互作分析 | `env_region_correlation_analysis` | 计算跨区域环境相关性并绘制热图。 |
| 表型、环境与互作分析 | `environment_index_analysis` | 执行 CERIS 风格环境指数分析。 |
| 表型、环境与互作分析 | `reaction_norm_analysis` | 估计反应范式的截距和斜率。 |
| 表型、环境与互作分析 | `variance_decomposition_analysis` | 分解表型中的基因型、环境和残差方差。 |
| 表型、环境与互作分析 | `gene_environment_interaction_analysis` | 进行 SNP 与环境因子的互作方差分析。 |
| 表型、环境与互作分析 | `locus_locus_interaction_analysis` | 基于 VCF、表型和基因映射文件进行基因间互作分析。 |
| 育种值评估与预测 | `heritability` | 估计性状遗传力。 |
| 育种值评估与预测 | `gebv_analysis` | 估计基因组育种值（GEBV）。 |
| 育种值评估与预测 | `rrblup_prediction_analysis` | 使用 rrBLUP 执行基因组预测。 |
| 育种值评估与预测 | `combining_ability_analysis` | 估计雌雄亲本 GCA 与杂交组合 SCA。 |
| 育种值评估与预测 | `qei_detection_analysis` | 进行多环境 QEI 检测。 |
| 关联定位与功能解释 | `gwas_analysis` | 执行 GWAS 关联分析。 |
| 关联定位与功能解释 | `candidate_gene_extraction_analysis` | 使用物种基因 BED 资源，通过 LD 窗口扩展提取玉米、小麦或水稻候选基因。 |
| 关联定位与功能解释 | `gene_function_annotation_analysis` | 进行 GO/KEGG 富集分析。 |
| 关联定位与功能解释 | `wheat_rice_gene_function_enrichment_analysis` | 使用用户管理的物种数据库进行小麦或水稻离线 GO/KEGG 富集分析。 |
| 关联定位与功能解释 | `protein_function_annotation_analysis` | 提取给定玉米基因列表对应蛋白的功能/结构域注释。 |
| 关联定位与功能解释 | `pfam_enrichment_analysis` | 对玉米、小麦或水稻进行流式 PFAM/结构域富集分析。 |
| 关联定位与功能解释 | `ortholog_extraction_analysis` | 使用物种矩阵资源提取玉米、小麦或水稻同源基因记录。 |
| 关联定位与功能解释 | `peak_annotation_analysis` | 对玉米、小麦或水稻 BED 区间进行位点结构注释。 |


## 主要特点 :balloon:

- 功能创新: 聚焦基因组育种分析任务，具备常用技能
- 能力稳定：采用skills+tools结构，确保分析能力稳定
- 后台执行：长时间需求会作为 agentic workflow 运行，并可稍后查询状态/结果
- 读取优化: 针对基因组育种分析中常见的VCF等文件进行优化，避免读取文件造成的上下文过长
- Research模式: 分析结果不带入Memory, 避免多次分析流程相互影响
- 多渠道使用：既可 CLI 使用，也可接入消息平台
- 研究友好：可以通过 tool、agentic workflow、skill 的组合快速扩展能力


## 安装 :electric_plug:

推荐优先使用 Docker 安装。Docker 镜像会内置 EasyGS 和分析环境，用户只需要
挂载配置/工作区目录和数据目录即可运行。

### 推荐方式：Docker

依赖要求：

- Linux x86_64、Bash 和 curl
- Git、Docker Engine 和 Docker Compose；优先使用 `docker compose` v2，也兼容
  系统软件仓库提供的 `docker-compose`；检测到缺失时可在用户确认后使用 `sudo` 自动安装
- 可用的 LLM provider/API key
- 两个宿主机目录：
  - `easygs-home`：挂载到 `/home/easygs/.easygs`，用于保存 `config.json`、
    工作区输出、外部资源、历史记录和运行状态。
  - `data`：挂载到 `/data`，用于保存用户数据。对话中请使用容器内路径引用文件，
    例如 `/data/example.vcf.gz`。

#### 一键安装

Linux x86_64 主机可以执行；缺少 Git、Docker 或 Compose 时安装器会询问是否补齐：

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | bash
```

脚本默认安装到 `~/easygs`，从 GitHub 获取最新源码，构建包含五套分析环境的镜像并
启动 EasyGS。安装过程中会交互选择 LLM provider，并通过隐藏输入配置 API key、
API Base 和默认模型。首次构建需要下载较多依赖。自定义安装位置、数据目录或 Git 分支：

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
  bash -s -- --install-dir "$HOME/apps/easygs" --data-dir "$HOME/easygs-data" --ref master
```

发布公共镜像后，可以跳过本地构建并直接拉取：

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
  bash -s -- --image <registry>/<namespace>/easygs:analysis
```

安装配置保存在 `~/easygs/.env`。重复运行脚本会更新源码和容器，同时保留其中的
模型、API key、飞书和邮件配置。缺少宿主机依赖时，脚本会先说明需要 `sudo` 并征求
确认，不会静默修改系统。Mamba、R 和生信分析工具只安装在 Docker 镜像内部。
在无人值守服务器或 CI 中使用 `--non-interactive` 可跳过 API 配置向导，之后再编辑
`.env`。若同时允许安装缺失的宿主机依赖，可执行：

```bash
curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
  bash -s -- --install-deps --non-interactive
```

#### 方式 A：使用现成镜像

使用根目录下的 `docker-compose.yml`。这个文件不包含 `build:`，会直接拉取
已经发布的镜像。

```bash
cd /path/to/easygs
cp .env.example .env
mkdir -p ./easygs-home ./data
# 编辑 .env：把 EASYGS_IMAGE 设置为已发布镜像，并填写模型/provider key。
docker compose pull
docker compose up -d
```

#### 方式 B：本地构建镜像

使用 `container/` 目录下的 compose 文件。这个文件就是构建用的，保留本地
`build:` 配置。

```bash
cd /path/to/easygs
cd container
cp .env.example .env
mkdir -p ./easygs-home /path/to/data
# 编辑 .env：设置 EASYGS_HOME_DIR、EASYGS_DATA_DIR、模型和 provider key。
docker compose build
docker compose up -d
```

首次启动时，容器会在 `easygs-home` 下自动补齐 EasyGS 需要的文件和目录，
包括 `config.json`、`workspace/`、`resources/`、`history/`、`run/` 和
`cron/`。如果这些文件或目录已经存在，容器会保留原内容。

浏览器打开：

```text
http://127.0.0.1:25685
```

外部资源不会打包进镜像。需要资源的功能请把资源放到
`easygs-home/resources/` 下。

更多 Docker 细节见 [container/README.md](container/README.md)。

### 可选方式：本地安装

本地安装主要适合开发者，或希望自己管理科学分析依赖的用户。

依赖要求：

- Python 3.11+
- 可用的 LLM provider 配置
- 如果要运行科学分析工作流，建议准备 conda 或 mamba

安装 EasyGS：

```bash
pip install easygs-0.1.0-py3-none-any.whl
```

EasyGS 的技能需要五个依赖环境：

- `EasyGS_1`
- `EasyGS_2`
- `EasyGS_3`
- `EasyGS_4`
- `EasyGS_5`

使用以下命令安装依赖环境：

```bash
conda env create -f env_all/EasyGS_1.yml
conda env create -f env_all/EasyGS_2.yml
conda env create -f env_all/EasyGS_3.yml
conda env create -f env_all/EasyGS_4.yml
conda env create -f env_all/EasyGS_5.yml
```
不同工作流会根据各自依赖的 R、Python 和命令行工具绑定到不同环境。每个工作流在执行前都会先检查环境是否存在，并在依赖缺失时返回清晰错误。

`fastq_to_vcf_analysis` 使用 `EasyGS_5` conda 环境，因为原始流程依赖
fastp、BWA、samtools、Picard、GATK、bgzip 和 tabix。

## 外部资源 :open_file_folder:

部分工作流需要大型参考文件，这些文件不会随 EasyGS 一起提供。用户手动管理的资源默认放在：

```text
~/.easygs/resources/
```

如果需要使用其他资源根目录，可以设置 `EASYGS_RESOURCES_DIR`。

### `fastq_to_vcf_analysis`

玉米 B73 v4 参考基因组及索引：

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

工具接收一个 FASTQ 目录，其中可包含任意数量的
`<sample_id>_1.fq.gz` / `<sample_id>_2.fq.gz` 配对样本。参考基因组与辅助脚本路径不是
公开参数。输出保留原流程的 `01-QC`、`02-Mapping`、`03-VariantCalling`、`04-Output`
和 `logs` 目录结构。

### `candidate_gene_extraction_analysis`

物种基因区间资源：

```text
~/.easygs/resources/candidate_gene_extraction_analysis/allV4gene.bed
~/.easygs/resources/candidate_gene_extraction_analysis/allwheatgene.bed
~/.easygs/resources/candidate_gene_extraction_analysis/allricegene.bed
```

工具接收位点 BED、`species=maize/wheat/rice`、LD 距离和可选输出前缀，自动选择对应
基因 BED。资源路径不是公开参数。输出包括扩展 BED、排序去重的候选基因列表、位点与
基因的详细匹配 TSV 和摘要文件。

### `protein_function_annotation_analysis` / `pfam_enrichment_analysis`

物种资源文件：

```text
~/.easygs/resources/pfam_enrichment_analysis/all_maize_longest_cds.txt
~/.easygs/resources/pfam_enrichment_analysis/all_maize_genes_proteins.fa.tsv
~/.easygs/resources/pfam_enrichment_analysis/wheat_interpro.tsv
~/.easygs/resources/pfam_enrichment_analysis/Osativa_323_v7.0.protein_primaryTranscriptOnly.fa.tsv
```

蛋白功能注释仍仅支持玉米并使用前两个文件。PFAM 富集接受 `species=maize/wheat/rice` 并自动选择对应资源，资源路径不是公开参数。小麦和水稻的多 GB InterProScan 文件采用流式处理，匹配前自动移除数字转录本后缀。

### `peak_annotation_analysis`

必需的物种资源文件：

```text
~/.easygs/resources/peak_annotation_analysis/Zea_mays.B73_RefGen_v4.43_modify.gff3
~/.easygs/resources/peak_annotation_analysis/Taestivumcv_ChineseSpring_725_v2.1.gene.gff3
~/.easygs/resources/peak_annotation_analysis/Osativa_323_v7.0.gene.gff3
```

工具只接收 BED 文件和物种 `species`（`maize`、`wheat` 或 `rice`），随后自动选择对应 GFF3；GFF3 路径不是公开工具参数。为兼容原有调用，默认物种仍为玉米。资源缺失或 BED 与 GFF3 染色体名称不一致时，工具会在运行前返回具体错误。

### `ortholog_extraction_analysis`

必需的物种资源文件：

```text
~/.easygs/resources/ortholog_extraction_analysis/maize_ortholog_matrix.tsv
~/.easygs/resources/ortholog_extraction_analysis/wheat_ortholog_matrix.tsv
~/.easygs/resources/ortholog_extraction_analysis/rice_ortholog_matrix.tsv
```

工具只接收基因列表和 `species`，自动选择对应矩阵，并对矩阵第一列进行完整基因 ID 精确匹配；矩阵路径不是公开参数。默认输出会移除输入文件名末尾的 `_genes`，例如 `100_wheat_genes.txt` 输出 `100_wheat.ortholog.tsv`。

### `wheat_rice_gene_function_enrichment_analysis`

必需文件：

```text
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/wheat_gene_KO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/rice_gene_KO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/taes_KEGG_annotation.txt
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/rice_KEGG_annotation.txt
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/wheat_gene_GO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/rice_gene_GO_one2one.tsv
~/.easygs/resources/wheat_rice_gene_function_enrichment_analysis/GO_term_table_2026.7.16.tsv
```

工具只要求用户提供基因列表和物种，自动从资源目录选择对应的 GO/KO 映射及注释数据库。正常使用时不需要传入这些资源文件的路径。

## 快速开始 :bicyclist:

先初始化本地配置和工作区：

```bash
easygs onboard
```

这会创建：

- 配置文件：`~/.easygs/config.json`
- EasyGS 工作区模板文件
- 资源目录：`~/.easygs/resources/`

然后在 `~/.easygs/config.json` 中填写 provider 凭证，再执行一次简单对话：

```bash
easygs agent -m "Hello, EasyGS"
```
连续对话:
```bash
easygs agent
```
待加载完成后即可持续对话。

如果要使用飞书等渠道接入：

```bash
easygs gateway
```
然后参照[飞书](docs/feishu_zh.md)等渠道的配置教程进行配置。

常用 CLI 命令包括：

- `easygs onboard`: EasyGS初始化，只需要在第一次安装时执行一次
- `easygs agent`: 开始与EasyGS持续对话
- `easygs gateway`: 启用EasyGS网关服务，支持飞书等渠道接入
- `easygs status`: 检查EasyGS的状态

## WebUI :computer:

EasyGS 可以通过 websocket channel 提供纯文本浏览器界面。在
`~/.easygs/config.json` 中启用：

```json
{ "channels": { "websocket": { "enabled": true, "port": 25685 } } }
```

然后启动：

```bash
easygs gateway
```

浏览器打开 `http://127.0.0.1:25685`。EasyGS WebUI 当前有意不启用图片或媒体上传。

## 配置 :golf:

默认配置文件路径：

```text
~/.easygs/config.json
```

配置文件主要控制：

- LLM provider 与默认模型
- 消息渠道
- 邮件通知
- 工作区行为

EasyGS 通过 provider registry 进行模型路由。当前支持配置文件中存在的提供商

## Research Mode 与分析工作流 :violin:

EasyGS 区分普通聊天使用和分析型使用。对于科学分析工作流，建议使用 research mode，避免多次分析流程的结果相互影响。EasyGS默认启用Research mode.

## 典型工作流行为 :book:

1. 用户提供需求，和文件路径和关键参数
2. EasyGS 检查必需文件以及环境/工具是否存在
3. 工作流在指定 conda 环境中运行
4. 输出写入目标目录
5. 生成 summary 文件，用于结果返回

在未显式指定 `output_dir` 时，EasyGS会把结果写到类似下面的默认目录：

```text
~/.easygs/workflows/runs/<workflow_id>/actions/<action_id>
```
除非用户显式指定 `output_dir`

## 通过飞书等渠道使用EasyGS :microphone:

除了 CLI方式，EasyGS 也可以运行在多个消息渠道上:

- Telegram
- [Feishu](docs/feishu.md) (Recommend)
- Discord
- DingTalk
- Slack
- QQ
- Email
- WhatsApp
- Mochat

渠道配置位于 `~/.easygs/config.json`。

## 如何扩展 EasyGS :headphones:

EasyGS 被设计成容易扩展。新增一个工作流通常包括：

1. 在 `easygs/agent/tools` 下增加新 tool
2. 为工具实现 `prepare_run()` 和 `to_metadata()` 以支持 workflow action 执行
3. 在 `easygs/agent/workflows.py` 中注册 workflow action
4. 如需要领域指导，在 `easygs/skills` 下增加 skill 目录

## 许可证 :book:

EasyGS 使用 MIT License 发布。

## 致谢 :gift:

本项目受 [HKUDS](https://github.com/HKUDS) 开源的 [nanobot](https://github.com/HKUDS/nanobot) 启发，并基于其架构进行构建。
我们衷心感谢原作者的开源贡献。
