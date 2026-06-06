#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  genotype_imputation.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --jar <beagle.jar> \
    --output-prefix <prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_genotype_imputation.py>

Required tools:
  java
  python3
EOF
}

vcf_file=""
jar_path=""
output_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --jar) jar_path="$2"; shift 2 ;;
    --output-prefix) output_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$vcf_file" "$jar_path" "$output_prefix" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in java python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

if [ ! -f "$vcf_file" ]; then
  echo "VCF file not found: $vcf_file" >&2
  exit 1
fi

if [ ! -f "$jar_path" ]; then
  echo "Beagle jar not found: $jar_path" >&2
  exit 1
fi

case "$vcf_file" in
  *.vcf|*.vcf.gz) ;;
  *)
    echo "VCF input must end with .vcf or .vcf.gz: $vcf_file" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$output_prefix")"
mkdir -p "$(dirname "$summary_output")"

java -jar "$jar_path" gt="$vcf_file" out="$output_prefix"

python3 "$summary_script" \
  --input-vcf "$vcf_file" \
  --jar "$jar_path" \
  --output-prefix "$output_prefix" \
  --output "$summary_output"

echo "Genotype imputation completed."
echo "Imputed VCF.GZ: ${output_prefix}.vcf.gz"
echo "Beagle log: ${output_prefix}.log"
echo "Summary file: ${summary_output}"
