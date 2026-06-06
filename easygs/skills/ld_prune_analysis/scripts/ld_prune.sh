#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  ld_prune.sh \
    (--vcf <input.vcf|input.vcf.gz> | --bfile <prefix>) \
    --out-prefix <prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_ld_prune.py> \
    --window-size <int> \
    --step-size <int> \
    --r2-threshold <float>

Required tools:
  plink
  python3
EOF
}

vcf_file=""
bfile_prefix=""
out_prefix=""
summary_output=""
summary_script=""
window_size=""
step_size=""
r2_threshold=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --window-size) window_size="$2"; shift 2 ;;
    --step-size) step_size="$2"; shift 2 ;;
    --r2-threshold) r2_threshold="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [ -z "$out_prefix" ] || [ -z "$summary_output" ] || [ -z "$summary_script" ] || [ -z "$window_size" ] || [ -z "$step_size" ] || [ -z "$r2_threshold" ]; then
  echo "Missing required arguments." >&2
  usage >&2
  exit 1
fi

if [ -n "$vcf_file" ] && [ -n "$bfile_prefix" ]; then
  echo "Provide exactly one of --vcf or --bfile." >&2
  exit 1
fi

if [ -z "$vcf_file" ] && [ -z "$bfile_prefix" ]; then
  echo "Provide exactly one of --vcf or --bfile." >&2
  exit 1
fi

for tool in plink python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

if [ -n "$vcf_file" ]; then
  plink --vcf "$vcf_file" --indep-pairwise "$window_size" "$step_size" "$r2_threshold" --out "$out_prefix"
  input_label="vcf"
  input_value="$vcf_file"
else
  plink --bfile "$bfile_prefix" --indep-pairwise "$window_size" "$step_size" "$r2_threshold" --out "$out_prefix"
  input_label="bfile"
  input_value="$bfile_prefix"
fi

python3 "$summary_script" \
  --prune-in "${out_prefix}.prune.in" \
  --prune-out "${out_prefix}.prune.out" \
  --output "$summary_output" \
  --input-label "$input_label" \
  --input-value "$input_value"

echo "LD pruning completed."
echo "Prune-in file: ${out_prefix}.prune.in"
echo "Prune-out file: ${out_prefix}.prune.out"
echo "Summary file: ${summary_output}"
