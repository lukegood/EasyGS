#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  rrblup_prediction.sh \
    --genotype-csvs <g1.csv,g2.csv> \
    --phenotype-csvs <p1.csv,p2.csv> \
    --cv-csvs <cv1.csv,cv2.csv> \
    --trait-name <X100grainweight> \
    --id-column <ID> \
    --cv-column <cv_1> \
    --expected-folds <10> \
    --output-dir <outdir> \
    --output-prefix <rrBLUP_X100grainweight> \
    --fold-metrics-output <fold_metrics.csv> \
    --mean-effect-output <mean_effect.csv> \
    --mean-intercept-output <mean_intercept.csv> \
    --summary-output <summary.txt> \
    --r-script <run_rrblup_prediction.R> \
    --summary-script <summarize_rrblup_prediction.py>

Required tools:
  Rscript
  python3

Environment:
  Run inside EasyGS_3 or with:
    mamba run -n EasyGS_3 bash rrblup_prediction.sh ...
EOF
}

genotype_csvs=""
phenotype_csvs=""
cv_csvs=""
trait_name=""
id_column=""
cv_column=""
expected_folds=""
output_dir=""
output_prefix=""
fold_metrics_output=""
mean_effect_output=""
mean_intercept_output=""
summary_output=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --genotype-csvs) genotype_csvs="$2"; shift 2 ;;
    --phenotype-csvs) phenotype_csvs="$2"; shift 2 ;;
    --cv-csvs) cv_csvs="$2"; shift 2 ;;
    --trait-name) trait_name="$2"; shift 2 ;;
    --id-column) id_column="$2"; shift 2 ;;
    --cv-column) cv_column="$2"; shift 2 ;;
    --expected-folds) expected_folds="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --output-prefix) output_prefix="$2"; shift 2 ;;
    --fold-metrics-output) fold_metrics_output="$2"; shift 2 ;;
    --mean-effect-output) mean_effect_output="$2"; shift 2 ;;
    --mean-intercept-output) mean_intercept_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$genotype_csvs" \
  "$phenotype_csvs" \
  "$cv_csvs" \
  "$trait_name" \
  "$id_column" \
  "$cv_column" \
  "$expected_folds" \
  "$output_dir" \
  "$output_prefix" \
  "$fold_metrics_output" \
  "$mean_effect_output" \
  "$mean_intercept_output" \
  "$summary_output" \
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

if ! Rscript -e "suppressPackageStartupMessages(library(rrBLUP))" >/dev/null 2>&1; then
  echo "Required R package not available in EasyGS_3: rrBLUP" >&2
  exit 1
fi

old_ifs=$IFS
IFS=','
set -- $genotype_csvs
for path in "$@"; do
  if [ ! -f "$path" ]; then
    echo "Required genotype CSV not found: $path" >&2
    exit 1
  fi
done
set -- $phenotype_csvs
for path in "$@"; do
  if [ ! -f "$path" ]; then
    echo "Required phenotype CSV not found: $path" >&2
    exit 1
  fi
done
set -- $cv_csvs
for path in "$@"; do
  if [ ! -f "$path" ]; then
    echo "Required CV CSV not found: $path" >&2
    exit 1
  fi
done
IFS=$old_ifs

for input_file in "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required script not found: $input_file" >&2
    exit 1
  fi
done

mkdir -p "$output_dir"
mkdir -p "$(dirname "$fold_metrics_output")"
mkdir -p "$(dirname "$mean_effect_output")"
mkdir -p "$(dirname "$mean_intercept_output")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --genotype-csvs "$genotype_csvs" \
  --phenotype-csvs "$phenotype_csvs" \
  --cv-csvs "$cv_csvs" \
  --trait-name "$trait_name" \
  --id-column "$id_column" \
  --cv-column "$cv_column" \
  --expected-folds "$expected_folds" \
  --output-dir "$output_dir" \
  --output-prefix "$output_prefix" \
  --fold-metrics-output "$fold_metrics_output" \
  --mean-effect-output "$mean_effect_output" \
  --mean-intercept-output "$mean_intercept_output"

python3 "$summary_script" \
  --genotype-csvs "$genotype_csvs" \
  --phenotype-csvs "$phenotype_csvs" \
  --cv-csvs "$cv_csvs" \
  --trait-name "$trait_name" \
  --id-column "$id_column" \
  --cv-column "$cv_column" \
  --expected-folds "$expected_folds" \
  --output-dir "$output_dir" \
  --output-prefix "$output_prefix" \
  --fold-metrics-output "$fold_metrics_output" \
  --mean-effect-output "$mean_effect_output" \
  --mean-intercept-output "$mean_intercept_output" \
  --summary-output "$summary_output"

echo "rrBLUP genomic prediction completed."
echo "Fold metrics CSV: $fold_metrics_output"
echo "Mean effect CSV: $mean_effect_output"
echo "Mean intercept CSV: $mean_intercept_output"
echo "Summary file: $summary_output"
