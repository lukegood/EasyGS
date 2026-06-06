#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  peak_annotation.sh \
    --gff3 <annotation.gff3> \
    --bed <locilist.bed> \
    --output-tsv <locilist.peakanno.tsv> \
    --output-png <locilist.peakanno.png> \
    --summary-output <summary.txt> \
    --tss-upstream <2000> \
    --tss-downstream <500> \
    --r-script <run_peak_annotation.R> \
    --summary-script <summarize_peak_annotation.py>

Required tools:
  Rscript
  python3

Required R packages:
  ChIPseeker
  GenomicFeatures
  ggplot2
  txdbmaker
  dplyr

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash peak_annotation.sh ...
EOF
}

gff3=""
bed=""
output_tsv=""
output_png=""
summary_output=""
tss_upstream=""
tss_downstream=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --gff3) gff3="$2"; shift 2 ;;
    --bed) bed="$2"; shift 2 ;;
    --output-tsv) output_tsv="$2"; shift 2 ;;
    --output-png) output_png="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --tss-upstream) tss_upstream="$2"; shift 2 ;;
    --tss-downstream) tss_downstream="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$gff3" \
  "$bed" \
  "$output_tsv" \
  "$output_png" \
  "$summary_output" \
  "$tss_upstream" \
  "$tss_downstream" \
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

for input_file in "$gff3" "$bed" "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

missing_packages="$(
  Rscript -e "pkgs <- c('ChIPseeker','GenomicFeatures','ggplot2','txdbmaker','dplyr'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$output_tsv")"
mkdir -p "$(dirname "$output_png")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --gff3 "$gff3" \
  --bed "$bed" \
  --output-tsv "$output_tsv" \
  --output-png "$output_png" \
  --tss-upstream "$tss_upstream" \
  --tss-downstream "$tss_downstream"

python3 "$summary_script" \
  --gff3 "$gff3" \
  --bed "$bed" \
  --output-tsv "$output_tsv" \
  --output-png "$output_png" \
  --summary-output "$summary_output" \
  --tss-upstream "$tss_upstream" \
  --tss-downstream "$tss_downstream"

echo "Peak annotation analysis completed."
echo "Annotation TSV: $output_tsv"
echo "Annotation PNG: $output_png"
echo "Summary file: $summary_output"
