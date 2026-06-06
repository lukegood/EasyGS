#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  environment_index.sh \
    --env-meta <Env_meta_table.txt> \
    --trait-records <Trait_records.txt> \
    --env-paras <5Envs_envParas_DAP150.txt> \
    --output-dir <output_dir> \
    --trait-label <trait_label> \
    --trait-column <trait_column> \
    --searching-daps <int> \
    --max-window-start <int> \
    --max-window-end <int> \
    --key-parameter <name> \
    --run-downstream <0|1> \
    --env-meta-encoding <encoding> \
    --r-script <run_environment_index.R> \
    --subfunctions-script <Sub_functions.r> \
    --summary-script <summarize_environment_index.py>

Required tools:
  Rscript
  python3

Required R packages:
  dplyr
  tidyr
  corrgram
  colorspace

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash environment_index.sh ...
EOF
}

env_meta=""
trait_records=""
env_paras=""
output_dir=""
trait_label=""
trait_column=""
searching_daps=""
max_window_start=""
max_window_end=""
key_parameter=""
run_downstream=""
env_meta_encoding=""
r_script=""
subfunctions_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-meta) env_meta="$2"; shift 2 ;;
    --trait-records) trait_records="$2"; shift 2 ;;
    --env-paras) env_paras="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --trait-label) trait_label="$2"; shift 2 ;;
    --trait-column) trait_column="$2"; shift 2 ;;
    --searching-daps) searching_daps="$2"; shift 2 ;;
    --max-window-start) max_window_start="$2"; shift 2 ;;
    --max-window-end) max_window_end="$2"; shift 2 ;;
    --key-parameter) key_parameter="$2"; shift 2 ;;
    --run-downstream) run_downstream="$2"; shift 2 ;;
    --env-meta-encoding) env_meta_encoding="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --subfunctions-script) subfunctions_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$env_meta" \
  "$trait_records" \
  "$env_paras" \
  "$output_dir" \
  "$trait_label" \
  "$trait_column" \
  "$searching_daps" \
  "$max_window_start" \
  "$max_window_end" \
  "$key_parameter" \
  "$run_downstream" \
  "$env_meta_encoding" \
  "$r_script" \
  "$subfunctions_script" \
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

for input_file in "$env_meta" "$trait_records" "$env_paras" "$r_script" "$subfunctions_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

if ! Rscript -e "pkgs <- c('dplyr','tidyr','corrgram','colorspace'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) stop(paste('Missing R packages:', paste(missing, collapse=', ')))" >/dev/null 2>&1; then
  echo "Required R packages not available: dplyr, tidyr, corrgram, colorspace" >&2
  exit 1
fi

mkdir -p "$output_dir"

Rscript "$r_script" \
  --env-meta "$env_meta" \
  --trait-records "$trait_records" \
  --env-paras "$env_paras" \
  --output-dir "$output_dir" \
  --trait-label "$trait_label" \
  --trait-column "$trait_column" \
  --searching-daps "$searching_daps" \
  --max-window-start "$max_window_start" \
  --max-window-end "$max_window_end" \
  --key-parameter "$key_parameter" \
  --run-downstream "$run_downstream" \
  --env-meta-encoding "$env_meta_encoding" \
  --subfunctions-script "$subfunctions_script"

python3 "$summary_script" \
  --env-meta "$env_meta" \
  --trait-records "$trait_records" \
  --env-paras "$env_paras" \
  --output-dir "$output_dir" \
  --trait-label "$trait_label" \
  --trait-column "$trait_column" \
  --run-downstream "$run_downstream" \
  --output "$output_dir/environment_index_summary.txt"

echo "Environment index analysis completed."
echo "Output dir: $output_dir"
echo "Trait output dir: $output_dir/$trait_label"
echo "allwinds_EF_cor.csv: $output_dir/allwinds_EF_cor.csv"
echo "highest_EF.csv: $output_dir/highest_EF.csv"
echo "Run downstream: $run_downstream"
echo "Summary file: $output_dir/environment_index_summary.txt"
