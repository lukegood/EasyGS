#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="${IMAGE_NAME:-easygs}"

if [[ "${1:-}" != "" && "${1:-}" != --* ]]; then
  TAG="$1"
  shift
else
  TAG="analysis"
fi

echo "Building ${IMAGE_NAME}:${TAG}"
echo "Context: ${PROJECT_ROOT}"
echo "Dockerfile: ${SCRIPT_DIR}/Dockerfile"

docker build \
  -f "$SCRIPT_DIR/Dockerfile" \
  -t "${IMAGE_NAME}:${TAG}" \
  "$@" \
  "$PROJECT_ROOT"

echo
echo "Built ${IMAGE_NAME}:${TAG}"
echo "Run with:"
echo "  docker run --rm -it --network host -v /path/to/easygs-home:/home/easygs/.easygs -v /path/to/data:/data ${IMAGE_NAME}:${TAG}"
