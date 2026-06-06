#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  phenotype_blup.sh \
    --input-csv <9地区株高.csv> \
    --output-csv <9地区下株高BLUP值.csv> \
    --summary-output <summary.txt> \
    --r-script <run_phenotype_blup.R> \
    --summary-script <summarize_phenotype_blup.py>

Required tools:
  Rscript
  python3

Required R packages:
  lme4
  reshape2
  dplyr

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash phenotype_blup.sh ...
EOF
}

input_csv=""
output_csv=""
summary_output=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input-csv) input_csv="$2"; shift 2 ;;
    --output-csv) output_csv="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$input_csv" "$output_csv" "$summary_output" "$r_script" "$summary_script"; do
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
  Rscript -e "pkgs <- c('lme4','reshape2','dplyr'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_csv")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --input-csv "$input_csv" \
  --output-csv "$output_csv"

python3 "$summary_script" \
  --input-csv "$input_csv" \
  --output-csv "$output_csv" \
  --output "$summary_output"

echo "Phenotype BLUP analysis completed."
echo "BLUP CSV: $output_csv"
echo "Summary file: $summary_output"
