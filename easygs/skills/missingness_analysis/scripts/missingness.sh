#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  missingness.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_missingness.py> \
    --sample-threshold <float> \
    --variant-threshold <float>

Required tools:
  plink
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash missingness.sh ...
EOF
}

vcf_file=""
out_prefix=""
summary_output=""
summary_script=""
sample_threshold="0.05"
variant_threshold="0.05"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --sample-threshold) sample_threshold="$2"; shift 2 ;;
    --variant-threshold) variant_threshold="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$vcf_file" "$out_prefix" "$summary_output" "$summary_script"; do
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

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

plink --vcf "$vcf_file" --missing --out "$out_prefix"

python3 "$summary_script" \
  --imiss "${out_prefix}.imiss" \
  --lmiss "${out_prefix}.lmiss" \
  --output "$summary_output" \
  --sample-threshold "$sample_threshold" \
  --variant-threshold "$variant_threshold"

echo "Missingness analysis completed."
echo "Sample missingness: ${out_prefix}.imiss"
echo "Variant missingness: ${out_prefix}.lmiss"
echo "Summary file: ${summary_output}"
