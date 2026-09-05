#!/usr/bin/env bash
set -Eeuo pipefail

readonly DEFAULT_REPO_URL="https://github.com/lukegood/EasyGS.git"
readonly DEFAULT_REF="master"

INSTALL_DIR="${EASYGS_INSTALL_DIR:-${HOME:-}/easygs}"
DATA_DIR="${EASYGS_DATA_DIR:-}"
REPO_URL="${EASYGS_REPO_URL:-$DEFAULT_REPO_URL}"
REF="${EASYGS_REF:-$DEFAULT_REF}"
MODE="${EASYGS_INSTALL_MODE:-build}"
IMAGE="${EASYGS_IMAGE:-}"
START=1
NON_INTERACTIVE="${EASYGS_NON_INTERACTIVE:-0}"
INSTALL_DEPS="${EASYGS_INSTALL_DEPS:-ask}"
DOCKER=(docker)
COMPOSE=(docker compose)
DOCKER_INSTALLER=""
BEAGLE_RESOURCE_MISSING=0

log() {
  printf '\n==> %s\n' "$*"
}

stage_running() {
  printf '    running...\n'
}

stage_finish() {
  printf '    finish.\n'
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Install or update EasyGS with Docker.

Usage:
  install.sh [options]

Options:
  --install-dir DIR  Installation root (default: $HOME/easygs)
  --data-dir DIR     Host data directory (default: INSTALL_DIR/data)
  --repo URL         EasyGS Git repository
  --ref REF          Git branch or tag (default: master)
  --build            Build the image locally from the selected Git ref (default)
  --image IMAGE      Pull and run a published image instead of building locally
  --no-start         Prepare/build/pull without starting EasyGS
  --non-interactive  Skip the interactive API configuration wizard
  --install-deps     Install missing Git, Docker, and Compose with sudo
  --no-install-deps  Do not offer to install missing host dependencies
  -h, --help         Show this help

Environment equivalents:
  EASYGS_INSTALL_DIR, EASYGS_DATA_DIR, EASYGS_REPO_URL, EASYGS_REF,
  EASYGS_INSTALL_MODE (build or pull), EASYGS_IMAGE, EASYGS_NON_INTERACTIVE,
  EASYGS_INSTALL_DEPS (ask, yes, or no)

Examples:
  curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | bash
  curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
    bash -s -- --image cloudcollector/easygs:latest
  curl -fsSL https://raw.githubusercontent.com/lukegood/EasyGS/master/install.sh | \
    bash -s -- --install-deps --non-interactive
EOF
}

require_value() {
  [[ $# -ge 2 && -n "$2" ]] || die "$1 requires a value"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      require_value "$@"
      INSTALL_DIR="$2"
      shift 2
      ;;
    --data-dir)
      require_value "$@"
      DATA_DIR="$2"
      shift 2
      ;;
    --repo)
      require_value "$@"
      REPO_URL="$2"
      shift 2
      ;;
    --ref)
      require_value "$@"
      REF="$2"
      shift 2
      ;;
    --build)
      MODE="build"
      IMAGE=""
      shift
      ;;
    --image)
      require_value "$@"
      MODE="pull"
      IMAGE="$2"
      shift 2
      ;;
    --no-start)
      START=0
      shift
      ;;
    --non-interactive)
      NON_INTERACTIVE=1
      shift
      ;;
    --install-deps)
      INSTALL_DEPS=yes
      shift
      ;;
    --no-install-deps)
      INSTALL_DEPS=no
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1 (use --help)"
      ;;
  esac
done

[[ -n "${HOME:-}" ]] || die "HOME is not set"
[[ "$MODE" == "build" || "$MODE" == "pull" ]] || \
  die "EASYGS_INSTALL_MODE must be 'build' or 'pull'"
[[ "$MODE" != "pull" || -n "$IMAGE" ]] || \
  die "pull mode requires --image IMAGE or EASYGS_IMAGE"
case "${NON_INTERACTIVE,,}" in
  0|false|no) NON_INTERACTIVE=0 ;;
  1|true|yes) NON_INTERACTIVE=1 ;;
  *) die "EASYGS_NON_INTERACTIVE must be 0/1, true/false, or yes/no" ;;
esac
case "${INSTALL_DEPS,,}" in
  ask) INSTALL_DEPS=ask ;;
  1|true|yes) INSTALL_DEPS=yes ;;
  0|false|no) INSTALL_DEPS=no ;;
  *) die "EASYGS_INSTALL_DEPS must be ask, yes, or no" ;;
esac

[[ "$(uname -s)" == "Linux" ]] || \
  die "EasyGS Docker installation currently supports Linux hosts only"

if [[ "$MODE" == "build" ]]; then
  case "$(uname -m)" in
    x86_64|amd64) ;;
    *) die "local image builds currently support Linux x86_64/amd64 only" ;;
  esac
fi

command -v curl >/dev/null 2>&1 || \
  die "curl is required to download the installer and Docker packages"

cleanup() {
  if [[ -n "$DOCKER_INSTALLER" && -f "$DOCKER_INSTALLER" ]]; then
    rm -f "$DOCKER_INSTALLER"
  fi
}
trap cleanup EXIT

run_root() {
  if [[ "$EUID" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    die "installing system dependencies requires root or sudo"
  fi
}

confirm_dependency_install() {
  local answer

  if [[ "$INSTALL_DEPS" == "yes" ]]; then
    return 0
  fi
  if [[ "$INSTALL_DEPS" == "no" || "$NON_INTERACTIVE" -eq 1 ]]; then
    return 1
  fi
  if ! { exec 8<>/dev/tty; } 2>/dev/null; then
    return 1
  fi
  printf 'Install missing host dependencies now? This requires sudo. [y/N]: ' >&8
  IFS= read -r answer <&8 || answer=""
  exec 8>&-
  case "${answer,,}" in
    y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

install_git() {
  log "Installing Git"
  if command -v apt-get >/dev/null 2>&1; then
    run_root apt-get update
    run_root apt-get install -y git
  elif command -v dnf >/dev/null 2>&1; then
    run_root dnf install -y git
  elif command -v yum >/dev/null 2>&1; then
    run_root yum install -y git
  elif command -v zypper >/dev/null 2>&1; then
    run_root zypper --non-interactive install git
  else
    die "no supported package manager was found to install Git"
  fi
}

install_docker() {
  log "Installing Docker Engine from Docker's official convenience script"
  DOCKER_INSTALLER="$(mktemp "${TMPDIR:-/tmp}/get-docker.XXXXXX.sh")"
  curl --proto '=https' --tlsv1.2 -fsSL https://get.docker.com -o "$DOCKER_INSTALLER"
  run_root sh "$DOCKER_INSTALLER"
  rm -f "$DOCKER_INSTALLER"
  DOCKER_INSTALLER=""
}

compose_is_available() {
  docker compose version >/dev/null 2>&1 || \
    { command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; }
}

install_compose() {
  log "Installing Docker Compose"
  if command -v apt-get >/dev/null 2>&1; then
    run_root apt-get update
    if run_root apt-get install -y docker-compose-plugin && compose_is_available; then
      return
    fi
    if run_root apt-get install -y docker-compose-v2 && compose_is_available; then
      return
    fi
    run_root apt-get install -y docker-compose
  elif command -v dnf >/dev/null 2>&1; then
    if run_root dnf install -y docker-compose-plugin && compose_is_available; then
      return
    fi
    run_root dnf install -y docker-compose
  elif command -v yum >/dev/null 2>&1; then
    if run_root yum install -y docker-compose-plugin && compose_is_available; then
      return
    fi
    run_root yum install -y docker-compose
  else
    die "install Docker Compose from https://docs.docker.com/compose/install/linux/"
  fi
}

start_docker_service() {
  if command -v systemctl >/dev/null 2>&1; then
    run_root systemctl enable --now docker
  elif command -v service >/dev/null 2>&1; then
    run_root service docker start
  fi
}

missing_dependencies=()
command -v git >/dev/null 2>&1 || missing_dependencies+=(Git)
command -v docker >/dev/null 2>&1 || missing_dependencies+=("Docker Engine")
if command -v docker >/dev/null 2>&1 && ! compose_is_available; then
  missing_dependencies+=("Docker Compose")
fi

if [[ "${#missing_dependencies[@]}" -gt 0 ]]; then
  log "Missing host dependencies: ${missing_dependencies[*]}"
  confirm_dependency_install || \
    die "dependencies were not installed; rerun with --install-deps or install them manually"
  command -v git >/dev/null 2>&1 || install_git
  command -v docker >/dev/null 2>&1 || install_docker
  if ! compose_is_available; then
    install_compose
  fi
fi

command -v git >/dev/null 2>&1 || die "Git installation failed"
command -v docker >/dev/null 2>&1 || die "Docker installation failed"
compose_is_available || die "Docker Compose installation failed"

if ! docker info >/dev/null 2>&1; then
  start_docker_service
fi
if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
elif [[ "$EUID" -ne 0 ]] && command -v sudo >/dev/null 2>&1 && \
    sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
else
  die "cannot access the Docker daemon; check the Docker service and permissions"
fi

if "${DOCKER[@]}" compose version >/dev/null 2>&1; then
  COMPOSE=("${DOCKER[@]}" compose)
elif command -v docker-compose >/dev/null 2>&1; then
  if [[ "${DOCKER[0]}" == "sudo" ]]; then
    COMPOSE=(sudo docker-compose)
  else
    COMPOSE=(docker-compose)
  fi
  "${COMPOSE[@]}" version >/dev/null 2>&1 || \
    die "the docker-compose command is installed but cannot run"
else
  die "neither 'docker compose' nor 'docker-compose' is available"
fi

mkdir -p "$INSTALL_DIR"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd -P)"
APP_DIR="$INSTALL_DIR/app"
ENV_FILE="$INSTALL_DIR/.env"
EASYGS_HOME_DIR="$INSTALL_DIR/easygs-home"

if [[ -z "$DATA_DIR" ]]; then
  DATA_DIR="$INSTALL_DIR/data"
fi
mkdir -p "$DATA_DIR"
DATA_DIR="$(cd "$DATA_DIR" && pwd -P)"

log "Fetching EasyGS ($REF)"
stage_running
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" diff --quiet || \
    die "$APP_DIR contains local tracked changes; commit or remove them before updating"
  git -C "$APP_DIR" diff --cached --quiet || \
    die "$APP_DIR contains staged changes; commit or remove them before updating"
  git -C "$APP_DIR" fetch --depth 1 origin "$REF"
  git -C "$APP_DIR" checkout --detach FETCH_HEAD
elif [[ -e "$APP_DIR" ]]; then
  die "$APP_DIR exists but is not an EasyGS Git checkout"
else
  git clone --depth 1 --branch "$REF" "$REPO_URL" "$APP_DIR"
fi
stage_finish

if [[ "$MODE" == "build" && ! -f "$APP_DIR/softwares/beagle.29Oct24.c8e.jar" ]]; then
  BEAGLE_RESOURCE_MISSING=1
  mkdir -p "$APP_DIR/softwares"
  : > "$APP_DIR/softwares/.easygs-resource-placeholder"
fi

set_env_value() {
  local key="$1"
  local value="$2"
  local file="$3"
  local temporary

  [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || \
    die "$key contains an unsupported newline"
  temporary="$(mktemp "$INSTALL_DIR/.env.tmp.XXXXXX")"
  ENV_VALUE="$value" awk -v key="$key" '
    BEGIN { found = 0; value = ENVIRON["ENV_VALUE"] }
    index($0, key "=") == 1 { print key "=" value; found = 1; next }
    { print }
    END { if (!found) print key "=" value }
  ' "$file" > "$temporary"
  mv "$temporary" "$file"
}

has_api_configuration() {
  awk '
    /^(CUSTOM|ANTHROPIC|OPENAI|OPENROUTER|DEEPSEEK|GROQ|ZHIPU|DASHSCOPE|VLLM|GEMINI|MOONSHOT|STEPFUN|MINIMAX|AIHUBMIX)_API_KEY=.+/ {
      found = 1
    }
    END { exit !found }
  ' "$ENV_FILE"
}

read_tty() {
  local prompt="$1"
  local default_value="${2:-}"

  if [[ -n "$default_value" ]]; then
    printf '%s [%s]: ' "$prompt" "$default_value" >&3
  else
    printf '%s: ' "$prompt" >&3
  fi
  IFS= read -r REPLY <&3 || die "interactive input ended unexpectedly"
  if [[ -z "$REPLY" ]]; then
    REPLY="$default_value"
  fi
}

confirm_tty() {
  local prompt="$1"
  local default_answer="$2"

  while true; do
    if [[ "$default_answer" == "yes" ]]; then
      read_tty "$prompt [Y/n]"
    else
      read_tty "$prompt [y/N]"
    fi
    case "${REPLY,,}" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      "") [[ "$default_answer" == "yes" ]] && return 0 || return 1 ;;
      *) printf 'Please enter y or n.\n' >&3 ;;
    esac
  done
}

configure_api() {
  local choice provider api_key api_base model default_model
  local prompt="Configure an LLM provider now?"
  local default_answer="yes"

  if [[ "$NON_INTERACTIVE" -eq 1 ]]; then
    log "Skipping API configuration (--non-interactive)"
    return
  fi
  if ! { exec 3<>/dev/tty; } 2>/dev/null; then
    log "No interactive terminal detected; configure API settings in $ENV_FILE"
    return
  fi
  if has_api_configuration; then
    prompt="An API key is already configured. Update it?"
    default_answer="no"
  fi
  if ! confirm_tty "$prompt" "$default_answer"; then
    exec 3>&-
    return
  fi

  cat >&3 <<'EOF'

Select an LLM provider:
  1) DeepSeek
  2) Zhipu / Z.AI
  3) MiniMax
  4) Bailian / Qwen
  5) Kimi
  6) Custom / OpenAI-compatible
  7) Skip
EOF

  while true; do
    read_tty "Provider" "1"
    choice="$REPLY"
    case "$choice" in
      1) provider="DEEPSEEK"; default_model="deepseek-v4-pro"; break ;;
      2) provider="ZHIPU"; default_model="glm-5.1"; break ;;
      3) provider="MINIMAX"; default_model="MiniMax-M2.7"; break ;;
      4) provider="DASHSCOPE"; default_model="qwen-3.6-plus"; break ;;
      5) provider="MOONSHOT"; default_model="kimi-k2.6"; break ;;
      6) provider="CUSTOM"; default_model="custom/model-name"; break ;;
      7) exec 3>&-; return ;;
      *) printf 'Please select 1-7.\n' >&3 ;;
    esac
  done

  printf 'API key (input hidden): ' >&3
  IFS= read -r -s api_key <&3 || die "interactive input ended unexpectedly"
  printf '\n' >&3
  [[ -n "$api_key" ]] || die "API key cannot be empty"

  read_tty "API base URL (optional)"
  api_base="$REPLY"
  if [[ "$provider" == "CUSTOM" && -z "$api_base" ]]; then
    die "API base URL is required for a custom provider"
  fi
  read_tty "Model" "$default_model"
  model="$REPLY"
  [[ -n "$model" ]] || die "model cannot be empty"

  set_env_value "${provider}_API_KEY" "$api_key" "$ENV_FILE"
  set_env_value "${provider}_API_BASE" "$api_base" "$ENV_FILE"
  set_env_value EASYGS_MODEL "$model" "$ENV_FILE"
  printf 'API configuration saved for %s.\n' "$provider" >&3
  exec 3>&-
}

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$APP_DIR/container/.env.example" "$ENV_FILE"
fi
set_env_value EASYGS_HOME_DIR "$EASYGS_HOME_DIR" "$ENV_FILE"
set_env_value EASYGS_DATA_DIR "$DATA_DIR" "$ENV_FILE"
configure_api

if [[ "$MODE" == "pull" ]]; then
  set_env_value EASYGS_IMAGE "$IMAGE" "$ENV_FILE"
  COMPOSE_FILE="$APP_DIR/docker-compose.yml"
else
  IMAGE="easygs:analysis"
  set_env_value EASYGS_IMAGE "$IMAGE" "$ENV_FILE"
  COMPOSE_FILE="$APP_DIR/container/docker-compose.yml"
fi

mkdir -p "$EASYGS_HOME_DIR"

compose() {
  "${COMPOSE[@]}" \
    --project-name easygs \
    --env-file "$ENV_FILE" \
    --file "$COMPOSE_FILE" \
    "$@"
}

print_banner() {
  local message="$1"
  local accent=""
  local bold=""
  local reset=""

  if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    accent=$'\033[36m'
    bold=$'\033[1m'
    reset=$'\033[0m'
  fi
  printf '\n%b%b' "$accent" "$bold"
  cat <<'EOF'
  ______                 _____  _____
 |  ____|               / ____|/ ____|
 | |__   __ _ ___ _   _| |  __| (___
 |  __| / _` / __| | | | | |_ |\___ \
 | |___| (_| \__ \ |_| | |__| |____) |
 |______\__,_|___/\__, |\_____|_____/
                   __/ |
                  |___/
EOF
  printf '%b\n' "$reset"
  printf '%b%s%b\n' "$bold" "$message" "$reset"
}

if [[ "$MODE" == "pull" ]]; then
  log "Pulling $IMAGE"
  stage_running
  "${DOCKER[@]}" pull "$IMAGE"
  stage_finish
else
  log "Building $IMAGE (the first build downloads all five analysis environments)"
  stage_running
  compose build
  stage_finish
fi

if [[ "$START" -eq 1 ]]; then
  log "Starting EasyGS"
  stage_running
  compose up -d --no-build
  compose ps
  stage_finish
  print_banner "EasyGS installation complete. The analysis workspace is ready."
else
  print_banner "EasyGS image preparation complete. Start the service when ready."
fi

cat <<EOF

  Web UI:       http://127.0.0.1:25685
  Installation: $INSTALL_DIR
  Configuration: $ENV_FILE
  EasyGS home:  $EASYGS_HOME_DIR
  Data:         $DATA_DIR

Edit provider/model settings in $ENV_FILE, then apply them with:
  ${COMPOSE[*]} --project-name easygs --env-file "$ENV_FILE" --file "$COMPOSE_FILE" up -d
EOF

if [[ "$BEAGLE_RESOURCE_MISSING" -eq 1 ]]; then
  cat <<EOF

Warning: the bundled Beagle resource was not present in the selected Git ref.
EasyGS was installed without genotype imputation support. Other workflows are available.

To enable genotype imputation later, place beagle.29Oct24.c8e.jar in:
  $APP_DIR/softwares/

Then rebuild and restart EasyGS:
  ${COMPOSE[*]} --project-name easygs --env-file "$ENV_FILE" --file "$COMPOSE_FILE" build
  ${COMPOSE[*]} --project-name easygs --env-file "$ENV_FILE" --file "$COMPOSE_FILE" up -d --no-build
EOF
fi
