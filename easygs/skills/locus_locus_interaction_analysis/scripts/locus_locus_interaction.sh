#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  locus_locus_interaction.sh \
    --vcf <input.vcf.gz> \
    --phenotype-csv <phenotype.csv> \
    --gene-map <gene_map.txt> \
    --output-dir <analysis_output_dir> \
    --threshold <float> \
    --summary-output <summary.txt> \
    --python-script <run_locus_locus_interaction.py> \
    --summary-script <summarize_locus_locus_interaction.py>

Required tools:
  python3

Required Python packages:
  pandas
  numpy
  statsmodels
  allel

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash locus_locus_interaction.sh ...
EOF
}

vcf=""
phenotype_csv=""
gene_map=""
output_dir=""
threshold=""
summary_output=""
python_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf="$2"; shift 2 ;;
    --phenotype-csv) phenotype_csv="$2"; shift 2 ;;
    --gene-map) gene_map="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --threshold) threshold="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --python-script) python_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$vcf" \
  "$phenotype_csv" \
  "$gene_map" \
  "$output_dir" \
  "$threshold" \
  "$summary_output" \
  "$python_script" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "Required tool not found on PATH: python3" >&2
  exit 1
fi

for input_file in "$vcf" "$phenotype_csv" "$gene_map" "$python_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

python3 -c "import pandas, numpy, statsmodels.api, allel" >/dev/null 2>&1 || {
  echo "Required Python packages are not available inside the current environment." >&2
  exit 1
}

mkdir -p "$output_dir"
mkdir -p "$(dirname "$summary_output")"

python3 "$python_script" \
  --vcf "$vcf" \
  --phenotype-csv "$phenotype_csv" \
  --gene-map "$gene_map" \
  --output-dir "$output_dir" \
  --threshold "$threshold"

python3 "$summary_script" \
  --vcf "$vcf" \
  --phenotype-csv "$phenotype_csv" \
  --gene-map "$gene_map" \
  --output-dir "$output_dir" \
  --summary-csv "$output_dir/gene_interaction_summary.csv" \
  --detail-csv "$output_dir/significant_snp_pairs_detailed.csv" \
  --report-path "$output_dir/analysis_report.txt" \
  --threshold "$threshold" \
  --output "$summary_output"

echo "Gene-by-gene interaction analysis completed."
echo "Output dir: $output_dir"
echo "Summary CSV: $output_dir/gene_interaction_summary.csv"
echo "Detailed CSV: $output_dir/significant_snp_pairs_detailed.csv"
echo "Analysis report: $output_dir/analysis_report.txt"
echo "Summary file: $summary_output"
