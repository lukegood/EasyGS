#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  nucleotide_diversity.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --mode <site|window> \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_nucleotide_diversity.py> \
    [--window-size <positive_integer>]

Required tools:
  vcftools
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash nucleotide_diversity.sh ...
EOF
}

vcf_file=""
mode=""
out_prefix=""
summary_output=""
summary_script=""
window_size=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --mode) mode="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --window-size) window_size="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$vcf_file" "$mode" "$out_prefix" "$summary_output" "$summary_script"; do
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

run_vcftools() {
  extra_flag="$1"
  extra_value="${2-}"

  case "$vcf_file" in
    *.vcf.gz)
      if [ -n "$extra_value" ]; then
        vcftools --gzvcf "$vcf_file" "$extra_flag" "$extra_value" --out "$out_prefix"
      else
        vcftools --gzvcf "$vcf_file" "$extra_flag" --out "$out_prefix"
      fi
      ;;
    *.vcf)
      if [ -n "$extra_value" ]; then
        vcftools --vcf "$vcf_file" "$extra_flag" "$extra_value" --out "$out_prefix"
      else
        vcftools --vcf "$vcf_file" "$extra_flag" --out "$out_prefix"
      fi
      ;;
    *)
      echo "VCF input must end with .vcf or .vcf.gz: $vcf_file" >&2
      exit 1
      ;;
  esac
}

case "$mode" in
  site)
    if [ -n "$window_size" ]; then
      echo "window_size can only be used when mode=window" >&2
      exit 1
    fi
    run_vcftools --site-pi
    result_path="${out_prefix}.sites.pi"
    ;;
  window)
    case "$window_size" in
      ''|*[!0-9]*)
        echo "window_size must be a positive integer in window mode" >&2
        exit 1
        ;;
    esac
    if [ "$window_size" -le 0 ]; then
      echo "window_size must be a positive integer in window mode" >&2
      exit 1
    fi
    run_vcftools --window-pi "$window_size"
    result_path="${out_prefix}.windowed.pi"
    ;;
  *)
    echo "mode must be one of: site, window" >&2
    exit 1
    ;;
esac

if [ -n "$window_size" ]; then
  python3 "$summary_script" \
    --mode "$mode" \
    --input-vcf "$vcf_file" \
    --result "$result_path" \
    --log "${out_prefix}.log" \
    --output "$summary_output" \
    --window-size "$window_size"
else
  python3 "$summary_script" \
    --mode "$mode" \
    --input-vcf "$vcf_file" \
    --result "$result_path" \
    --log "${out_prefix}.log" \
    --output "$summary_output"
fi

echo "Nucleotide-diversity analysis completed."
echo "Mode: ${mode}"
if [ -n "$window_size" ]; then
  echo "Window size: ${window_size}"
fi
echo "Result file: ${result_path}"
echo "vcftools log: ${out_prefix}.log"
echo "Summary file: ${summary_output}"
