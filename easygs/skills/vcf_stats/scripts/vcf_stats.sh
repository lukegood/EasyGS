#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  vcf_stats.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --stats-output <vcf_stats.txt> \
    --summary-output <cal.txt>

Required tools:
  bcftools
  grep

Notes:
  - Run this script inside the EasyGS_1 conda environment or with:
      mamba run -n EasyGS_1 bash vcf_stats.sh ...
EOF
}

vcf_file=""
stats_output=""
summary_output=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf)
      vcf_file="$2"
      shift 2
      ;;
    --stats-output)
      stats_output="$2"
      shift 2
      ;;
    --summary-output)
      summary_output="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

for required in "$vcf_file" "$stats_output" "$summary_output"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in bcftools grep; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

if [ ! -f "$vcf_file" ]; then
  echo "VCF file not found: $vcf_file" >&2
  exit 1
fi

case "$vcf_file" in
  *.vcf|*.vcf.gz)
    ;;
  *)
    echo "VCF input must end with .vcf or .vcf.gz: $vcf_file" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$stats_output")"
mkdir -p "$(dirname "$summary_output")"

bcftools stats "$vcf_file" > "$stats_output"
grep -E '^SN|^TSTV|^SiS|^# ST' "$stats_output" > "$summary_output"

echo "VCF statistics completed."
echo "Stats file: $stats_output"
echo "Summary file: $summary_output"
