#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  # Keep release builds aligned with the repository's Python environment.
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to build the EasyGS WebUI" >&2
  exit 1
fi

rm -rf "$ROOT_DIR/easygs/web/dist"

pushd "$ROOT_DIR/webui" >/dev/null
npm ci
npm run build
popd >/dev/null

if command -v uv >/dev/null 2>&1; then
  uv build
else
  python -m build
fi
