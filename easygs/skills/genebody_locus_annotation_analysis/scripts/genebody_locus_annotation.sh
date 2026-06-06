#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  genebody_locus_annotation.sh \
    --locus-list <locus_list.txt> \
    --site-gene-output <site_gene.txt> \
    --gene-output <genes.txt> \
    --summary-output <summary.txt> \
    --summary-script <summarize_genebody_locus_annotation.py> \
    --gene-bed <allV4gene.bed>

Required tools:
  bedtools
  python3
  awk
  sed
  cut

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash genebody_locus_annotation.sh ...
EOF
}

locus_list=""
site_gene_output=""
gene_output=""
summary_output=""
summary_script=""
gene_bed=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --locus-list) locus_list="$2"; shift 2 ;;
    --site-gene-output) site_gene_output="$2"; shift 2 ;;
    --gene-output) gene_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --gene-bed) gene_bed="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$locus_list" \
  "$site_gene_output" \
  "$gene_output" \
  "$summary_output" \
  "$summary_script" \
  "$gene_bed"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in bedtools python3 awk sed cut; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

if [ ! -f "$locus_list" ]; then
  echo "Required locus list not found: $locus_list" >&2
  exit 1
fi
if [ ! -f "$gene_bed" ]; then
  echo "Built-in gene BED not found: $gene_bed" >&2
  exit 1
fi
if [ ! -f "$summary_script" ]; then
  echo "Required summary script not found: $summary_script" >&2
  exit 1
fi

mkdir -p "$(dirname "$site_gene_output")"
mkdir -p "$(dirname "$gene_output")"
mkdir -p "$(dirname "$summary_output")"

awk -F '[.]s_' 'BEGIN{OFS="\t"} NF >= 2 {print $1, $2, $2 + 1, $0}' "$locus_list" \
  | sed 's/chr//g' \
  | bedtools intersect -a - -b "$gene_bed" -wa -wb \
  | cut -f4,8 \
  | sed 's/^/chr/g' > "$site_gene_output"

cut -f2 "$site_gene_output" > "$gene_output"

python3 "$summary_script" \
  --locus-list "$locus_list" \
  --gene-bed "$gene_bed" \
  --site-gene-output "$site_gene_output" \
  --gene-output "$gene_output" \
  --summary-output "$summary_output"

echo "Genebody locus annotation completed."
echo "Site-gene output: $site_gene_output"
echo "Gene output: $gene_output"
echo "Summary file: $summary_output"
