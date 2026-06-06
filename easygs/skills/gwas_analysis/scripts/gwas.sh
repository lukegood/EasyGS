#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  gwas.sh \
    --bfile-prefix <maize976> \
    --phenotype-csv <PH_intercep_IQR_values.csv> \
    --output-dir <output_dir> \
    --summary-output <summary.txt> \
    --line-column <LINE> \
    --trait-column <intercept> \
    --methods <GLM,MLM,FarmCPU> \
    --threshold <0.05> \
    --pcs-keep <5> \
    --npc-glm <5> \
    --npc-mlm <5> \
    --npc-farmcpu <5> \
    --ncpus <10> \
    --r-script <run_gwas.R> \
    --summary-script <summarize_gwas.py>

Required tools:
  Rscript
  python3

Required R packages:
  rMVP
  bigmemory

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash gwas.sh ...
EOF
}

bfile_prefix=""
phenotype_csv=""
output_dir=""
summary_output=""
line_column=""
trait_column=""
methods=""
threshold=""
pcs_keep=""
npc_glm=""
npc_mlm=""
npc_farmcpu=""
ncpus=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile-prefix) bfile_prefix="$2"; shift 2 ;;
    --phenotype-csv) phenotype_csv="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --line-column) line_column="$2"; shift 2 ;;
    --trait-column) trait_column="$2"; shift 2 ;;
    --methods) methods="$2"; shift 2 ;;
    --threshold) threshold="$2"; shift 2 ;;
    --pcs-keep) pcs_keep="$2"; shift 2 ;;
    --npc-glm) npc_glm="$2"; shift 2 ;;
    --npc-mlm) npc_mlm="$2"; shift 2 ;;
    --npc-farmcpu) npc_farmcpu="$2"; shift 2 ;;
    --ncpus) ncpus="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$bfile_prefix" \
  "$phenotype_csv" \
  "$output_dir" \
  "$summary_output" \
  "$line_column" \
  "$trait_column" \
  "$methods" \
  "$threshold" \
  "$pcs_keep" \
  "$npc_glm" \
  "$npc_mlm" \
  "$npc_farmcpu" \
  "$ncpus" \
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

for input_file in "$phenotype_csv" "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

missing_packages="$(
  Rscript -e "pkgs <- c('rMVP','bigmemory'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$output_dir"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --bfile-prefix "$bfile_prefix" \
  --phenotype-csv "$phenotype_csv" \
  --output-dir "$output_dir" \
  --line-column "$line_column" \
  --trait-column "$trait_column" \
  --methods "$methods" \
  --threshold "$threshold" \
  --pcs-keep "$pcs_keep" \
  --npc-glm "$npc_glm" \
  --npc-mlm "$npc_mlm" \
  --npc-farmcpu "$npc_farmcpu" \
  --ncpus "$ncpus"

python3 "$summary_script" \
  --bfile-prefix "$bfile_prefix" \
  --phenotype-csv "$phenotype_csv" \
  --output-dir "$output_dir" \
  --summary-output "$summary_output" \
  --trait-column "$trait_column" \
  --methods "$methods"

echo "GWAS analysis completed."
echo "Output dir: $output_dir"
echo "Summary file: $summary_output"
