#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  gene_environment_interaction.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --phenotype-csv <PH_phe.csv> \
    --env-csv <env_mean.csv> \
    --output-dir <analysis_output_dir> \
    --group-size <int> \
    --summary-output <summary.txt> \
    --python-script <run_gene_environment_interaction.py> \
    --summary-script <summarize_gene_environment_interaction.py> \
    [--max-workers <int>]

Required tools:
  python3

Required Python packages:
  numpy
  pandas
  statsmodels
  allel

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash gene_environment_interaction.sh ...
EOF
}

vcf=""
phenotype_csv=""
env_csv=""
output_dir=""
group_size=""
max_workers=""
summary_output=""
python_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf="$2"; shift 2 ;;
    --phenotype-csv) phenotype_csv="$2"; shift 2 ;;
    --env-csv) env_csv="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --group-size) group_size="$2"; shift 2 ;;
    --max-workers) max_workers="$2"; shift 2 ;;
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
  "$env_csv" \
  "$output_dir" \
  "$group_size" \
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

for input_file in "$vcf" "$phenotype_csv" "$env_csv" "$python_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

if ! python3 -c "import numpy; import pandas; import statsmodels.api; import allel" >/dev/null 2>&1; then
  echo "Required Python packages not available: numpy, pandas, statsmodels, allel" >&2
  exit 1
fi

mkdir -p "$output_dir"
mkdir -p "$(dirname "$summary_output")"

set -- \
  --vcf "$vcf" \
  --phenotype-csv "$phenotype_csv" \
  --env-csv "$env_csv" \
  --output-dir "$output_dir" \
  --group-size "$group_size"

if [ -n "$max_workers" ]; then
  set -- "$@" --max-workers "$max_workers"
fi

python3 "$python_script" "$@"

python3 "$summary_script" \
  --vcf "$vcf" \
  --phenotype-csv "$phenotype_csv" \
  --env-csv "$env_csv" \
  --output-dir "$output_dir" \
  --output "$summary_output"

echo "Gene-by-environment interaction analysis completed."
echo "Output dir: $output_dir"
echo "Env-factor result dir: $output_dir/env_factors"
echo "Summary file: $summary_output"
