#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  candidate_gene_extraction.sh \
    --bed <locilist.bed> \
    --ld-distance <50000> \
    --gene-bed <allV4gene.bed> \
    --extended-bed-output <locilist.extend.bed> \
    --gene-list-output <genelist.txt> \
    --summary-output <summary.txt> \
    --summary-script <summarize_candidate_gene_extraction.py>

Required tools:
  bedtools
  python3
  awk

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash candidate_gene_extraction.sh ...
EOF
}

bed=""
ld_distance=""
gene_bed=""
extended_bed_output=""
gene_list_output=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bed) bed="$2"; shift 2 ;;
    --ld-distance) ld_distance="$2"; shift 2 ;;
    --gene-bed) gene_bed="$2"; shift 2 ;;
    --extended-bed-output) extended_bed_output="$2"; shift 2 ;;
    --gene-list-output) gene_list_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$bed" \
  "$ld_distance" \
  "$gene_bed" \
  "$extended_bed_output" \
  "$gene_list_output" \
  "$summary_output" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in bedtools python3 awk; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

if [ ! -f "$bed" ]; then
  echo "Required BED file not found: $bed" >&2
  exit 1
fi
if [ ! -f "$gene_bed" ]; then
  echo "Required gene annotation BED not found: $gene_bed" >&2
  exit 1
fi
if [ ! -f "$summary_script" ]; then
  echo "Required summary script not found: $summary_script" >&2
  exit 1
fi

mkdir -p "$(dirname "$extended_bed_output")"
mkdir -p "$(dirname "$gene_list_output")"
mkdir -p "$(dirname "$summary_output")"

echo "使用LD距离: ${ld_distance}bp 进行位点区间扩展..."

awk -v OFS='\t' -v ld="$ld_distance" '{
  start = $2 - ld;
  if (start < 0) start = 0;
  print $1, start, $3 + ld
}' "$bed" > "$extended_bed_output"

bedtools intersect -a "$extended_bed_output" -b "$gene_bed" -wa -wb \
  | awk 'BEGIN{FS=OFS="\t"} NF >= 7 {print $7}' \
  | awk '!seen[$0]++' > "$gene_list_output"

python3 "$summary_script" \
  --bed "$bed" \
  --ld-distance "$ld_distance" \
  --gene-bed "$gene_bed" \
  --extended-bed-output "$extended_bed_output" \
  --gene-list-output "$gene_list_output" \
  --summary-output "$summary_output"

echo "操作完成。候选基因列表已保存至: $gene_list_output"
echo "Extended BED: $extended_bed_output"
echo "Summary file: $summary_output"
