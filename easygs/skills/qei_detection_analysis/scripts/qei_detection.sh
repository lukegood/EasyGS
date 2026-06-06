#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  qei_detection.sh \
    --bfile-prefix <maize976> \
    --phenotype-csv <testphe.csv> \
    --structure-csv <598.Q1.csv> \
    --output-prefix <res> \
    --summary-output <summary.txt> \
    --trait-count <1> \
    --n-en <4> \
    --phenotype-id-column <<Phenotype>> \
    --structure-id-column <<Structure>> \
    --geno-type <SNP> \
    --svrad <20000> \
    --svpal <0.01> \
    --svmlod <3> \
    --n-threads <10> \
    --draw-plot <FALSE> \
    --plot-format <*.tiff> \
    --r-script <run_qei_detection.R> \
    --summary-script <summarize_qei_detection.py>

Required tools:
  Rscript
  python3

Required R packages:
  Fast3VmrMLM

Environment:
  Run inside EasyGS_4 or with:
    mamba run -n EasyGS_4 bash qei_detection.sh ...
EOF
}

bfile_prefix=""
phenotype_csv=""
structure_csv=""
output_prefix=""
summary_output=""
trait_count=""
n_en=""
phenotype_id_column=""
structure_id_column=""
geno_type=""
svrad=""
svpal=""
svmlod=""
n_threads=""
draw_plot=""
plot_format=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile-prefix) bfile_prefix="$2"; shift 2 ;;
    --phenotype-csv) phenotype_csv="$2"; shift 2 ;;
    --structure-csv) structure_csv="$2"; shift 2 ;;
    --output-prefix) output_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --trait-count) trait_count="$2"; shift 2 ;;
    --n-en) n_en="$2"; shift 2 ;;
    --phenotype-id-column) phenotype_id_column="$2"; shift 2 ;;
    --structure-id-column) structure_id_column="$2"; shift 2 ;;
    --geno-type) geno_type="$2"; shift 2 ;;
    --svrad) svrad="$2"; shift 2 ;;
    --svpal) svpal="$2"; shift 2 ;;
    --svmlod) svmlod="$2"; shift 2 ;;
    --n-threads) n_threads="$2"; shift 2 ;;
    --draw-plot) draw_plot="$2"; shift 2 ;;
    --plot-format) plot_format="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$bfile_prefix" \
  "$phenotype_csv" \
  "$structure_csv" \
  "$output_prefix" \
  "$summary_output" \
  "$trait_count" \
  "$n_en" \
  "$phenotype_id_column" \
  "$structure_id_column" \
  "$geno_type" \
  "$svrad" \
  "$svpal" \
  "$svmlod" \
  "$n_threads" \
  "$draw_plot" \
  "$plot_format" \
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

for suffix in .bed .bim .fam; do
  if [ ! -f "${bfile_prefix}${suffix}" ]; then
    echo "Required BFILE component not found: ${bfile_prefix}${suffix}" >&2
    exit 1
  fi
done

for input_file in "$phenotype_csv" "$structure_csv" "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

missing_packages="$(
  Rscript -e "pkgs <- c('Fast3VmrMLM'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_prefix")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --bfile-prefix "$bfile_prefix" \
  --phenotype-csv "$phenotype_csv" \
  --structure-csv "$structure_csv" \
  --output-prefix "$output_prefix" \
  --trait-count "$trait_count" \
  --n-en "$n_en" \
  --phenotype-id-column "$phenotype_id_column" \
  --structure-id-column "$structure_id_column" \
  --geno-type "$geno_type" \
  --svrad "$svrad" \
  --svpal "$svpal" \
  --svmlod "$svmlod" \
  --n-threads "$n_threads" \
  --draw-plot "$draw_plot" \
  --plot-format "$plot_format"

python3 "$summary_script" \
  --bfile-prefix "$bfile_prefix" \
  --phenotype-csv "$phenotype_csv" \
  --structure-csv "$structure_csv" \
  --output-prefix "$output_prefix" \
  --summary-output "$summary_output" \
  --trait-count "$trait_count" \
  --n-en "$n_en" \
  --draw-plot "$draw_plot"

echo "QEI detection completed."
echo "Output prefix: $output_prefix"
echo "Summary file: $summary_output"
