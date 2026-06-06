#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  reaction_norm.sh \
    --input-csv <9地区株高.csv> \
    --long-output <用于计算斜率截距的表型文件.csv> \
    --slope-output <PH_intercep_slope_values.csv> \
    --summary-output <summary.txt> \
    --trait-label <PH> \
    --r-script <run_reaction_norm.R> \
    --summary-script <summarize_reaction_norm.py>

Required tools:
  Rscript
  python3

Required R packages:
  tidyr
  dplyr

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash reaction_norm.sh ...
EOF
}

input_csv=""
long_output=""
slope_output=""
summary_output=""
trait_label=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input-csv) input_csv="$2"; shift 2 ;;
    --long-output) long_output="$2"; shift 2 ;;
    --slope-output) slope_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --trait-label) trait_label="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$input_csv" "$long_output" "$slope_output" "$summary_output" "$trait_label" "$r_script" "$summary_script"; do
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
  Rscript -e "pkgs <- c('tidyr','dplyr'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$long_output")"
mkdir -p "$(dirname "$slope_output")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --input-csv "$input_csv" \
  --long-output "$long_output" \
  --slope-output "$slope_output" \
  --trait-label "$trait_label"

python3 "$summary_script" \
  --input-csv "$input_csv" \
  --long-output "$long_output" \
  --slope-output "$slope_output" \
  --trait-label "$trait_label" \
  --output "$summary_output"

echo "Reaction norm analysis completed."
echo "Long-format CSV: $long_output"
echo "Intercept/slope CSV: $slope_output"
echo "Summary file: $summary_output"
