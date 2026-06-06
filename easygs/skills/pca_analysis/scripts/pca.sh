#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  pca.sh \
    --bfile <prefix> \
    --components <int> \
    --out-prefix <prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_pca.py>

Required tools:
  plink
  python3
EOF
}

bfile_prefix=""
components=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --components) components="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$bfile_prefix" "$components" "$out_prefix" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in plink python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

case "$components" in
  ''|*[!0-9]*)
    echo "components must be a positive integer" >&2
    exit 1
    ;;
esac
if [ "$components" -le 0 ]; then
  echo "components must be a positive integer" >&2
  exit 1
fi

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

plink --bfile "$bfile_prefix" --pca "$components" --out "$out_prefix"

python3 "$summary_script" \
  --components "$components" \
  --input-bfile "$bfile_prefix" \
  --eigenval "${out_prefix}.eigenval" \
  --eigenvec "${out_prefix}.eigenvec" \
  --log "${out_prefix}.log" \
  --output "$summary_output"

echo "PCA analysis completed."
echo "Eigenvalue file: ${out_prefix}.eigenval"
echo "Eigenvector file: ${out_prefix}.eigenvec"
echo "PLINK log: ${out_prefix}.log"
echo "Summary file: ${summary_output}"
