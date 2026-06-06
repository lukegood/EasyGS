#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  population_structure_kinship.sh \
    --bfile <prefix> \
    --output-dir <dir> \
    --ld-window-size <int> \
    --ld-step-size <int> \
    --ld-r2-threshold <float> \
    --pca-components <int> \
    --k-min <int> \
    --k-max <int> \
    --ld-prune-prefix <prefix> \
    --ld-bfile-prefix <prefix> \
    --pca-prefix <prefix> \
    --grm-prefix <prefix> \
    --admixture-prefix <name> \
    --best-k-output <path> \
    --summary-output <summary.txt> \
    --summary-script <summarize_population_structure_kinship.py> \
    --ld-prune-script <ld_prune.sh> \
    --ld-prune-summary-script <summarize_ld_prune.py> \
    --bfile-extract-script <bfile_extract.sh> \
    --bfile-extract-summary-script <summarize_bfile_extract.py> \
    --pca-script <pca.sh> \
    --pca-summary-script <summarize_pca.py> \
    --grm-script <grm.sh> \
    --grm-summary-script <summarize_grm.py> \
    --admixture-script <admixture.sh> \
    --admixture-summary-script <summarize_admixture.py> \
    [--existing-ld-bfile <prefix>]
EOF
}

bfile_prefix=""
output_dir=""
ld_window_size=""
ld_step_size=""
ld_r2_threshold=""
pca_components=""
k_min=""
k_max=""
ld_prune_prefix=""
ld_bfile_prefix=""
pca_prefix=""
grm_prefix=""
admixture_prefix=""
best_k_output=""
summary_output=""
summary_script=""
ld_prune_script=""
ld_prune_summary_script=""
bfile_extract_script=""
bfile_extract_summary_script=""
pca_script=""
pca_summary_script=""
grm_script=""
grm_summary_script=""
admixture_script=""
admixture_summary_script=""
existing_ld_bfile=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --ld-window-size) ld_window_size="$2"; shift 2 ;;
    --ld-step-size) ld_step_size="$2"; shift 2 ;;
    --ld-r2-threshold) ld_r2_threshold="$2"; shift 2 ;;
    --pca-components) pca_components="$2"; shift 2 ;;
    --k-min) k_min="$2"; shift 2 ;;
    --k-max) k_max="$2"; shift 2 ;;
    --ld-prune-prefix) ld_prune_prefix="$2"; shift 2 ;;
    --ld-bfile-prefix) ld_bfile_prefix="$2"; shift 2 ;;
    --pca-prefix) pca_prefix="$2"; shift 2 ;;
    --grm-prefix) grm_prefix="$2"; shift 2 ;;
    --admixture-prefix) admixture_prefix="$2"; shift 2 ;;
    --best-k-output) best_k_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --ld-prune-script) ld_prune_script="$2"; shift 2 ;;
    --ld-prune-summary-script) ld_prune_summary_script="$2"; shift 2 ;;
    --bfile-extract-script) bfile_extract_script="$2"; shift 2 ;;
    --bfile-extract-summary-script) bfile_extract_summary_script="$2"; shift 2 ;;
    --pca-script) pca_script="$2"; shift 2 ;;
    --pca-summary-script) pca_summary_script="$2"; shift 2 ;;
    --grm-script) grm_script="$2"; shift 2 ;;
    --grm-summary-script) grm_summary_script="$2"; shift 2 ;;
    --admixture-script) admixture_script="$2"; shift 2 ;;
    --admixture-summary-script) admixture_summary_script="$2"; shift 2 ;;
    --existing-ld-bfile) existing_ld_bfile="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$bfile_prefix" "$output_dir" "$ld_window_size" "$ld_step_size" "$ld_r2_threshold" \
  "$pca_components" "$k_min" "$k_max" "$ld_prune_prefix" "$ld_bfile_prefix" \
  "$pca_prefix" "$grm_prefix" "$admixture_prefix" "$best_k_output" "$summary_output" \
  "$summary_script" "$ld_prune_script" "$ld_prune_summary_script" \
  "$bfile_extract_script" "$bfile_extract_summary_script" \
  "$pca_script" "$pca_summary_script" "$grm_script" "$grm_summary_script" \
  "$admixture_script" "$admixture_summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

mkdir -p "$output_dir"
mkdir -p "$(dirname "$best_k_output")"
mkdir -p "$(dirname "$summary_output")"

ld_prune_summary="${ld_prune_prefix}_summary.txt"
bfile_extract_summary="${ld_bfile_prefix}_summary.txt"
pca_summary="${pca_prefix}_summary.txt"
grm_summary="${grm_prefix}_summary.txt"
admixture_summary="${output_dir}/${admixture_prefix}_admixture_summary.txt"

if [ -n "$existing_ld_bfile" ]; then
  ld_dataset_prefix="$existing_ld_bfile"
  reuse_existing_ld_bfile="yes"
else
  ld_dataset_prefix="$ld_bfile_prefix"
  reuse_existing_ld_bfile="no"

  bash "$ld_prune_script" \
    --bfile "$bfile_prefix" \
    --out-prefix "$ld_prune_prefix" \
    --summary-output "$ld_prune_summary" \
    --summary-script "$ld_prune_summary_script" \
    --window-size "$ld_window_size" \
    --step-size "$ld_step_size" \
    --r2-threshold "$ld_r2_threshold"

  bash "$bfile_extract_script" \
    --bfile "$bfile_prefix" \
    --extract-file "${ld_prune_prefix}.prune.in" \
    --out-prefix "$ld_bfile_prefix" \
    --summary-output "$bfile_extract_summary" \
    --summary-script "$bfile_extract_summary_script"
fi

bash "$pca_script" \
  --bfile "$ld_dataset_prefix" \
  --components "$pca_components" \
  --out-prefix "$pca_prefix" \
  --summary-output "$pca_summary" \
  --summary-script "$pca_summary_script"

bash "$grm_script" \
  --bfile "$bfile_prefix" \
  --out-prefix "$grm_prefix" \
  --summary-output "$grm_summary" \
  --summary-script "$grm_summary_script"

bash "$admixture_script" \
  --bfile "$bfile_prefix" \
  --dataset-prefix "$admixture_prefix" \
  --output-dir "$output_dir" \
  --k-min "$k_min" \
  --k-max "$k_max" \
  --best-k-output "$best_k_output" \
  --summary-output "$admixture_summary" \
  --summary-script "$admixture_summary_script"

python3 "$summary_script" \
  --input-bfile "$bfile_prefix" \
  --output-dir "$output_dir" \
  --ld-prune-prefix "$ld_prune_prefix" \
  --ld-bfile-prefix "$ld_bfile_prefix" \
  --pca-prefix "$pca_prefix" \
  --grm-prefix "$grm_prefix" \
  --admixture-prefix "$admixture_prefix" \
  --ld-prune-summary "$ld_prune_summary" \
  --bfile-extract-summary "$bfile_extract_summary" \
  --pca-summary "$pca_summary" \
  --grm-summary "$grm_summary" \
  --admixture-summary "$admixture_summary" \
  --best-k-output "$best_k_output" \
  --reuse-existing-ld-bfile "$reuse_existing_ld_bfile" \
  --output "$summary_output"

echo "Population structure and kinship workflow completed."
echo "Summary file: ${summary_output}"
