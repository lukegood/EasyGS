# syntax=docker/dockerfile:1.6

FROM node:22-bookworm-slim AS webui-builder

ARG NPM_REGISTRY=https://registry.npmmirror.com

WORKDIR /src

COPY webui/package*.json webui/
RUN cd webui \
    && npm config set registry "${NPM_REGISTRY}" \
    && npm ci

COPY webui/ webui/
RUN cd webui && npm run build


FROM debian:bookworm-slim

ARG APT_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian
ARG APT_SECURITY_MIRROR=http://mirrors.tuna.tsinghua.edu.cn/debian-security
ARG CONDA_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/anaconda
ARG MINIFORGE_URL=https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-Linux-x86_64.sh
ARG NPM_REGISTRY=https://registry.npmmirror.com
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG EASYGS_UID=1000
ARG EASYGS_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV CONDA_DIR=/opt/conda
ENV PATH=/opt/conda/bin:$PATH
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONUNBUFFERED=1
ENV R_REPOS=https://mirrors.tuna.tsinghua.edu.cn/CRAN/

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
          -e "s|http://deb.debian.org/debian|${APT_MIRROR}|g" \
          -e "s|http://security.debian.org/debian-security|${APT_SECURITY_MIRROR}|g" \
          /etc/apt/sources.list.d/debian.sources; \
    else \
        printf 'deb %s bookworm main\n' "${APT_MIRROR}" > /etc/apt/sources.list; \
        printf 'deb %s bookworm-updates main\n' "${APT_MIRROR}" >> /etc/apt/sources.list; \
        printf 'deb %s bookworm-security main\n' "${APT_SECURITY_MIRROR}" >> /etc/apt/sources.list; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      bzip2 \
      ca-certificates \
      curl \
      git \
      gosu \
      procps \
      tini \
      unzip \
      wget \
      xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/miniforge.sh "${MINIFORGE_URL}" \
    && bash /tmp/miniforge.sh -b -p "${CONDA_DIR}" \
    && rm -f /tmp/miniforge.sh \
    && conda config --system --set show_channel_urls true \
    && cat > "${CONDA_DIR}/.condarc" <<EOF
channels:
  - conda-forge
  - bioconda
show_channel_urls: true
default_channels:
  - ${CONDA_MIRROR}/pkgs/main
  - ${CONDA_MIRROR}/pkgs/r
  - ${CONDA_MIRROR}/pkgs/msys2
custom_channels:
  conda-forge: ${CONDA_MIRROR}/cloud
  bioconda: ${CONDA_MIRROR}/cloud
channel_priority: strict
EOF

WORKDIR /app

COPY container/envs/ container/envs/
RUN set -eux; \
    mamba install -y -n base nodejs=22; \
    for env_file in container/envs/EasyGS_1.yml container/envs/EasyGS_2.yml container/envs/EasyGS_3.yml container/envs/EasyGS_4.yml; do \
      mamba env create --yes -f "${env_file}"; \
    done; \
    mamba run -n EasyGS_1 Rscript -e "install.packages('corrgram', repos=Sys.getenv('R_REPOS'))"; \
    mamba run -n EasyGS_2 Rscript -e "install.packages('sommer', repos=Sys.getenv('R_REPOS'))"; \
    mamba run -n EasyGS_4 Rscript -e "install.packages('Fast3VmrMLM', repos=Sys.getenv('R_REPOS'))"; \
    mamba clean -afy

RUN set -eux; \
    mamba install -y -n EasyGS_4 \
      r-rcpp \
      r-rcpparmadillo \
      r-rcppparallel \
      r-mass \
      r-openxlsx \
      r-bh \
      boost \
      tbb=2020.2; \
    mamba run -n EasyGS_4 Rscript -e "zip <- tempfile(fileext = '.zip'); root <- tempfile(); dir.create(root); download.file('https://github.com/YuanmingZhang65/Fast3VmrMLM/archive/refs/heads/main.zip', zip, mode = 'wb'); unzip(zip, exdir = root); unzip(file.path(root, 'Fast3VmrMLM-main', 'Fast3VmrMLM_Linux_2.0.zip'), exdir = root); install.packages(file.path(root, 'Fast3VmrMLM'), repos = NULL, type = 'source')"; \
    mamba clean -afy

COPY pyproject.toml README.md README_zh.md LICENSE ./
COPY easygs/ easygs/
COPY bridge/ bridge/
COPY softwares/ softwares/
COPY --from=webui-builder /src/easygs/web/dist easygs/web/dist

RUN find easygs/skills -type l -delete

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN cd bridge \
    && npm config set registry "${NPM_REGISTRY}" \
    && npm install \
    && npm run build \
    && npm cache clean --force

RUN groupadd --gid "${EASYGS_GID}" easygs \
    && useradd --uid "${EASYGS_UID}" --gid "${EASYGS_GID}" --create-home --home-dir /home/easygs --shell /bin/bash easygs \
    && mkdir -p /data /home/easygs/.easygs \
    && cp "${CONDA_DIR}/.condarc" /home/easygs/.condarc \
    && chown -R easygs:easygs /home/easygs /data

COPY container/entrypoint.sh /usr/local/bin/easygs-container-entrypoint
RUN chmod +x /usr/local/bin/easygs-container-entrypoint

ENV HOME=/home/easygs
WORKDIR /data

EXPOSE 25685

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/easygs-container-entrypoint"]
CMD []
