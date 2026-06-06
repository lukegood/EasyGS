# EasyGS Docker 使用指南

本文档介绍如何使用 Docker 运行 EasyGS。容器内已包含 EasyGS Python 包、Web UI、bridge 服务，以及 GS 分析工具所需的 conda 环境。

English version: [README.md](README.md).

## 什么时候使用 Docker

如果你希望在宿主机上不安装 conda、R 包、PLINK、bcftools 或 EasyGS 本体，同时获得统一的运行环境，可以使用 Docker。

容器运行时仍然需要挂载两个宿主机目录：

- `easygs-home`：挂载到 `/home/easygs/.easygs`，用于保存 `config.json`、工作区输出、资源文件、历史记录和运行状态。
- `data`：挂载到 `/data`，用于保存用户输入数据。

在 EasyGS 中引用输入数据时，请始终使用容器内路径 `/data/...`。

## 使用 Docker Compose 快速启动

在项目根目录执行：

```bash
cd /path/to/easygs
cp .env.example .env
mkdir -p ./easygs-home ./data
```

编辑 `.env`：

```dotenv
EASYGS_IMAGE=your-dockerhub-name/easygs:analysis
EASYGS_HOME_DIR=./easygs-home
EASYGS_DATA_DIR=./data

EASYGS_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_API_BASE=your-api-base
```

只需要填写你实际使用的 provider 凭证。常见 provider 包括 `DEEPSEEK_API_KEY`、`ZHIPU_API_KEY`、`MOONSHOT_API_KEY`、`MINIMAX_API_KEY`、`DASHSCOPE_API_KEY` 和 `CUSTOM_API_KEY`。

启动 EasyGS：

```bash
docker compose pull
docker compose up -d
```

打开 Web UI：

```text
http://127.0.0.1:25685
```

如果 EasyGS 运行在远程服务器上，请先在自己的电脑上建立端口转发：

```bash
ssh -L 25685:127.0.0.1:25685 user@server_ip
```

然后在本机浏览器打开 `http://127.0.0.1:25685`。

## 构建本地镜像

如果你希望从源码构建本地镜像：

```bash
cd /path/to/easygs
container/build.sh
```

默认会构建：

```text
easygs:analysis
```

构建脚本默认使用国内较友好的镜像源：

- Debian：TUNA
- Miniforge / conda：TUNA
- npm：npmmirror
- PyPI：TUNA

也可以在构建时切换镜像源：

```bash
container/build.sh analysis \
  --build-arg APT_MIRROR=http://mirrors.bfsu.edu.cn/debian \
  --build-arg APT_SECURITY_MIRROR=http://mirrors.bfsu.edu.cn/debian-security \
  --build-arg CONDA_MIRROR=https://mirrors.bfsu.edu.cn/anaconda \
  --build-arg MINIFORGE_URL=https://mirrors.bfsu.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-Linux-x86_64.sh
```

构建完成后，可以使用 `container/` 目录下的 compose 文件运行本地镜像：

```bash
cd container
cp .env.example .env
mkdir -p ./easygs-home /path/to/your/data
```

编辑 `container/.env`：

```dotenv
EASYGS_HOME_DIR=./easygs-home
EASYGS_DATA_DIR=/path/to/your/data

EASYGS_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_API_BASE=your-api-base
```

然后启动：

```bash
docker compose up -d
```

## 使用 `docker run`

也可以直接运行镜像：

```bash
docker run --rm -it \
  --network host \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v "$PWD/data:/data" \
  -e EASYGS_AGENTS__DEFAULTS__MODEL=deepseek-v4-pro \
  -e EASYGS_PROVIDERS__DEEPSEEK__API_KEY=your-api-key \
  -e EASYGS_PROVIDERS__DEEPSEEK__API_BASE=your-api-base \
  easygs:analysis
```

如果没有额外传入命令，容器会默认启动：

```bash
easygs gateway --research-mode
```

## 运行 EasyGS 命令

在镜像名后追加命令，可以运行 EasyGS CLI：

```bash
docker run --rm -it \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v "$PWD/data:/data" \
  easygs:analysis easygs status

docker run --rm -it \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v "$PWD/data:/data" \
  easygs:analysis easygs agent
```

## 工作区和外部资源

分析输出会写入容器内 EasyGS 工作区：

```text
/home/easygs/.easygs/workspace
```

使用上面的 compose 示例时，对应宿主机路径为：

```text
./easygs-home/workspace
```

部分工具需要大型参考文件，这些资源不会打包进镜像。请将外部资源放在：

```text
./easygs-home/resources
```

例如：

```text
./easygs-home/resources/pfam_enrichment_analysis/all_maize_longest_cds.txt
./easygs-home/resources/pfam_enrichment_analysis/all_maize_genes_proteins.fa.tsv
```

## 消息渠道和通知

Docker Compose 已提供飞书和独立 SMTP 通知相关环境变量。

飞书 / Lark 配置示例：

```dotenv
FEISHU_ENABLED=true
FEISHU_APP_ID=your-app-id
FEISHU_APP_SECRET=your-app-secret
FEISHU_ENCRYPT_KEY=your-encrypt-key
FEISHU_VERIFICATION_TOKEN=your-verification-token
FEISHU_ALLOW_FROM=[]
```

任务完成邮件通知配置示例：

```dotenv
EMAIL_NOTIFY_ENABLED=true
EMAIL_NOTIFY_SMTP_HOST=smtp.example.com
EMAIL_NOTIFY_SMTP_PORT=587
EMAIL_NOTIFY_SMTP_USERNAME=your-username
EMAIL_NOTIFY_SMTP_PASSWORD=your-password
EMAIL_NOTIFY_FROM_ADDRESS=from@example.com
EMAIL_NOTIFY_TO_ADDRESS=to@example.com
```

## 检查分析环境

镜像内包含 EasyGS 分析工具使用的 conda 环境：

```bash
docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v "$PWD/data:/data" \
  easygs:analysis conda env list

docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v "$PWD/data:/data" \
  easygs:analysis mamba run -n EasyGS_1 command -v bcftools

docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v "$PWD/data:/data" \
  easygs:analysis mamba run -n EasyGS_2 command -v plink
```

## 注意事项

- compose 文件使用 `network_mode: host`，Web UI 会在宿主机 `127.0.0.1:25685` 监听。
- 容器入口脚本要求同时挂载 `/home/easygs/.easygs` 和 `/data`。
- 如果 `config.json` 不存在，入口脚本会自动创建默认配置，然后应用 `EASYGS_...__...` 环境变量覆盖。
- 修改 `.env` 中的模型或 provider 配置后，请使用 `docker compose up -d` 重启容器。
