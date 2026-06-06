#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  combining_ability.sh \
    --input-csv <rand_hybrid.phe.csv> \
    --female-gca-output <Female_gca.csv> \
    --male-gca-output <Male_gca.csv> \
    --sca-output <sca.csv> \
    --summary-output <summary.txt> \
    --hybrid-column <Hybrid> \
    --female-column <Female> \
    --male-column <Male> \
    --phenotype-column <Phenotype> \
    --r-script <run_combining_ability.R> \
    --summary-script <summarize_combining_ability.py>

Required tools:
  Rscript
  python3

Required R packages:
  sommer
  lme4

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash combining_ability.sh ...
EOF
}

input_csv=""
female_gca_output=""
male_gca_output=""
sca_output=""
summary_output=""
hybrid_column=""
female_column=""
male_column=""
phenotype_column=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --input-csv) input_csv="$2"; shift 2 ;;
    --female-gca-output) female_gca_output="$2"; shift 2 ;;
    --male-gca-output) male_gca_output="$2"; shift 2 ;;
    --sca-output) sca_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --hybrid-column) hybrid_column="$2"; shift 2 ;;
    --female-column) female_column="$2"; shift 2 ;;
    --male-column) male_column="$2"; shift 2 ;;
    --phenotype-column) phenotype_column="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$input_csv" \
  "$female_gca_output" \
  "$male_gca_output" \
  "$sca_output" \
  "$summary_output" \
  "$hybrid_column" \
  "$female_column" \
  "$male_column" \
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
  Rscript -e "pkgs <- c('sommer','lme4'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$female_gca_output")"
mkdir -p "$(dirname "$male_gca_output")"
mkdir -p "$(dirname "$sca_output")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --input-csv "$input_csv" \
  --female-gca-output "$female_gca_output" \
  --male-gca-output "$male_gca_output" \
  --sca-output "$sca_output" \
  --hybrid-column "$hybrid_column" \
  --female-column "$female_column" \
  --male-column "$male_column" \
  --phenotype-column "$phenotype_column"

python3 "$summary_script" \
  --input-csv "$input_csv" \
  --female-gca-output "$female_gca_output" \
  --male-gca-output "$male_gca_output" \
  --sca-output "$sca_output" \
  --output "$summary_output"

echo "Combining ability analysis completed."
echo "Female GCA CSV: $female_gca_output"
echo "Male GCA CSV: $male_gca_output"
echo "SCA CSV: $sca_output"
echo "Summary file: $summary_output"
