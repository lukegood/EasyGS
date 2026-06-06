#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  allele_count.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_allele_count.py>

Required tools:
  vcftools
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash allele_count.sh ...
EOF
}

vcf_file=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
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

for tool in vcftools python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

case "$vcf_file" in
  *.vcf.gz)
    vcftools --gzvcf "$vcf_file" --counts --out "$out_prefix"
    ;;
  *.vcf)
    vcftools --vcf "$vcf_file" --counts --out "$out_prefix"
    ;;
  *)
    echo "VCF input must end with .vcf or .vcf.gz: $vcf_file" >&2
    exit 1
    ;;
esac

python3 "$summary_script" \
  --input-vcf "$vcf_file" \
  --count "${out_prefix}.frq.count" \
  --log "${out_prefix}.log" \
  --output "$summary_output"

echo "Allele-count analysis completed."
echo "Count file: ${out_prefix}.frq.count"
echo "vcftools log: ${out_prefix}.log"
echo "Summary file: ${summary_output}"
