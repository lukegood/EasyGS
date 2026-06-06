#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  vcf_variant_extract.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --variant-ids <variant_ids.txt> \
    --variant-ids-input-label <label> \
    --output-vcf <subset.vcf> \
    --summary-output <summary.txt> \
    --summary-script <summarize_vcf_variant_extract.py>

Required tools:
  bcftools
  python3

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash vcf_variant_extract.sh ...
EOF
}

vcf_file=""
variant_ids=""
variant_ids_input_label=""
output_vcf=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --variant-ids) variant_ids="$2"; shift 2 ;;
    --variant-ids-input-label) variant_ids_input_label="$2"; shift 2 ;;
    --output-vcf) output_vcf="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$vcf_file" "$variant_ids" "$variant_ids_input_label" "$output_vcf" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in bcftools python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for input_file in "$vcf_file" "$variant_ids" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$output_vcf")"
mkdir -p "$(dirname "$summary_output")"

bcftools view \
  -i "ID=@${variant_ids}" \
  "$vcf_file" \
  -O v \
  -o "$output_vcf"

python3 "$summary_script" \
  --vcf "$vcf_file" \
  --variant-ids-input-label "$variant_ids_input_label" \
  --variant-ids "$variant_ids" \
  --output-vcf "$output_vcf" \
  --output "$summary_output"

echo "VCF variant extraction completed."
echo "Variant IDs input: ${variant_ids_input_label}"
echo "Output VCF: ${output_vcf}"
echo "Summary file: ${summary_output}"
