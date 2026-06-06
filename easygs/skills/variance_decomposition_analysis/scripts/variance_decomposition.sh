#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  variance_decomposition.sh \
    --input-csv <用于计算斜率截距的表型文件.csv> \
    --output-csv <variance_components_percentage.csv> \
    --summary-output <variance_components_percentage_summary.txt> \
    --genotype-column <LINE> \
    --environment-column <location> \
    --phenotype-column <PH> \
    --r-script <run_variance_decomposition.R> \
    --summary-script <summarize_variance_decomposition.py>

Required tools:
  Rscript
  python3

Required R packages:
  lme4
  lmerTest

Environment:
  Run inside EasyGS_3 or with:
    mamba run -n EasyGS_3 bash variance_decomposition.sh ...
EOF
}

input_csv=""
output_csv=""
summary_output=""
genotype_column=""
environment_column=""
phenotype_column=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input-csv) input_csv="$2"; shift 2 ;;
    --output-csv) output_csv="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --genotype-column) genotype_column="$2"; shift 2 ;;
    --environment-column) environment_column="$2"; shift 2 ;;
    --phenotype-column) phenotype_column="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$input_csv" \
  "$output_csv" \
  "$summary_output" \
  "$genotype_column" \
  "$environment_column" \
  "$phenotype_column" \
  "$r_script" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in Rscript python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for input_file in "$input_csv" "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

missing_packages="$(
  Rscript -e "pkgs <- c('lme4','lmerTest'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_csv")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --input-csv "$input_csv" \
  --output-csv "$output_csv" \
  --genotype-column "$genotype_column" \
  --environment-column "$environment_column" \
  --phenotype-column "$phenotype_column"

python3 "$summary_script" \
  --input-csv "$input_csv" \
  --output-csv "$output_csv" \
  --output "$summary_output"

echo "Variance decomposition analysis completed."
echo "Result CSV: $output_csv"
echo "Summary file: $summary_output"

