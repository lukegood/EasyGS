# EasyGS Analysis Container

This container packages EasyGS with its analysis environments. It is intended
for users who want to mount data and run EasyGS without installing conda,
R, PLINK, bcftools, or the EasyGS Python package on the host.

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
  -e EASYGS_AGENTS__DEFAULTS__MODEL=anthropic/claude-opus-4-5 \
  -e EASYGS_PROVIDERS__ANTHROPIC__API_KEY=sk-xxx \
  easygs:analysis
```

With Docker Compose, copy `.env.example` to `.env` and set both required
directories:

```dotenv
EASYGS_HOME_DIR=./easygs-home
EASYGS_DATA_DIR=/path/to/data
```

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
  easygs:analysis mamba run -n EasyGS_1 command -v bcftools

docker run --rm \
  -v "$PWD/easygs-home:/home/easygs/.easygs" \
  -v /path/to/data:/data \
  easygs:analysis mamba run -n EasyGS_2 command -v plink
```
