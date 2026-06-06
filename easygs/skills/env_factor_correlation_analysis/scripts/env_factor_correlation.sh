#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  env_factor_correlation.sh \
    --input-csv <env.csv> \
    --region <region_name> \
    --cor-output <correlation.csv> \
    --pdf-output <heatmap.pdf> \
    --summary-output <summary.txt> \
    --r-script <env_factor_correlation_heatmap.R> \
    --summary-script <summarize_env_factor_correlation.py>

Required tools:
  Rscript
  python3

Required R package:
  corrplot

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash env_factor_correlation.sh ...
EOF
}

input_csv=""
region=""
cor_output=""
pdf_output=""
summary_output=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input-csv) input_csv="$2"; shift 2 ;;
    --region) region="$2"; shift 2 ;;
    --cor-output) cor_output="$2"; shift 2 ;;
    --pdf-output) pdf_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$input_csv" \
  "$region" \
  "$cor_output" \
  "$pdf_output" \
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

if [ ! -f "$input_csv" ]; then
  echo "Input CSV not found: $input_csv" >&2
  exit 1
fi

if ! Rscript -e "if (!requireNamespace('corrplot', quietly = TRUE)) stop('corrplot package is required')" >/dev/null 2>&1; then
  echo "Required R package not available: corrplot" >&2
  exit 1
fi

mkdir -p "$(dirname "$cor_output")"
mkdir -p "$(dirname "$pdf_output")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --input-csv "$input_csv" \
  --region "$region" \
  --cor-output "$cor_output" \
  --pdf-output "$pdf_output"

python3 "$summary_script" \
  --input-csv "$input_csv" \
  --region "$region" \
  --correlation-csv "$cor_output" \
  --heatmap-pdf "$pdf_output" \
  --output "$summary_output"

echo "Environmental-factor correlation analysis completed."
echo "Correlation CSV: $cor_output"
echo "Heatmap PDF: $pdf_output"
echo "Summary file: $summary_output"
