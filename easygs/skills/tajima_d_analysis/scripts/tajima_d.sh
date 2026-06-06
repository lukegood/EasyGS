#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  tajima_d.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --window-size <positive_integer> \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_tajima_d.py>

Required tools:
  vcftools
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash tajima_d.sh ...
EOF
}

vcf_file=""
window_size=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --window-size) window_size="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$vcf_file" "$window_size" "$out_prefix" "$summary_output" "$summary_script"; do
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

case "$window_size" in
  ''|*[!0-9]*)
    echo "window_size must be a positive integer" >&2
    exit 1
    ;;
esac
if [ "$window_size" -le 0 ]; then
  echo "window_size must be a positive integer" >&2
  exit 1
fi

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

case "$vcf_file" in
  *.vcf.gz)
    vcftools --gzvcf "$vcf_file" --TajimaD "$window_size" --out "$out_prefix"
    ;;
  *.vcf)
    vcftools --vcf "$vcf_file" --TajimaD "$window_size" --out "$out_prefix"
    ;;
  *)
    echo "VCF input must end with .vcf or .vcf.gz: $vcf_file" >&2
    exit 1
    ;;
esac

python3 "$summary_script" \
  --input-vcf "$vcf_file" \
  --window-size "$window_size" \
  --result "${out_prefix}.Tajima.D" \
  --log "${out_prefix}.log" \
  --output "$summary_output"

echo "Tajima's D analysis completed."
echo "Window size: ${window_size}"
echo "Tajima's D file: ${out_prefix}.Tajima.D"
echo "vcftools log: ${out_prefix}.log"
echo "Summary file: ${summary_output}"
