#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  admixture.sh \
    --bfile <prefix> \
    --dataset-prefix <name> \
    --output-dir <dir> \
    --k-min <int> \
    --k-max <int> \
    --best-k-output <path> \
    --summary-output <summary.txt> \
    --summary-script <summarize_admixture.py>

Required tools:
  admixture
  python3
EOF
}

bfile_prefix=""
dataset_prefix=""
output_dir=""
k_min=""
k_max=""
best_k_output=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --dataset-prefix) dataset_prefix="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --k-min) k_min="$2"; shift 2 ;;
    --k-max) k_max="$2"; shift 2 ;;
    --best-k-output) best_k_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$bfile_prefix" "$dataset_prefix" "$output_dir" "$k_min" "$k_max" "$best_k_output" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in admixture python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

case "$k_min" in
  ''|*[!0-9]*) echo "k_min must be an integer" >&2; exit 1 ;;
esac
case "$k_max" in
  ''|*[!0-9]*) echo "k_max must be an integer" >&2; exit 1 ;;
esac
if [ "$k_min" -lt 2 ]; then
  echo "k_min must be at least 2" >&2
  exit 1
fi
if [ "$k_max" -lt "$k_min" ]; then
  echo "k_max must be greater than or equal to k_min" >&2
  exit 1
fi

mkdir -p "$output_dir"
mkdir -p "$(dirname "$best_k_output")"
mkdir -p "$(dirname "$summary_output")"

for ext in bed bim fam; do
  src="${bfile_prefix}.${ext}"
  dst="${output_dir}/${dataset_prefix}.${ext}"
  if [ ! -f "$src" ]; then
    echo "Missing BFILE component: $src" >&2
    exit 1
  fi
  if [ "$src" != "$dst" ]; then
    ln -sf "$src" "$dst"
  fi
done

old_pwd=$(pwd)
cd "$output_dir"
k="$k_min"
while [ "$k" -le "$k_max" ]; do
  admixture --cv "${dataset_prefix}.bed" "$k" 2>&1 | tee "log${k}.out"
  k=$((k + 1))
done
cd "$old_pwd"

python3 "$summary_script" \
  --input-bfile "$bfile_prefix" \
  --output-dir "$output_dir" \
  --dataset-prefix "$dataset_prefix" \
  --k-min "$k_min" \
  --k-max "$k_max" \
  --best-k-output "$best_k_output" \
  --output "$summary_output"

echo "ADMIXTURE analysis completed."
echo "Best K result: ${best_k_output}"
echo "Summary file: ${summary_output}"
