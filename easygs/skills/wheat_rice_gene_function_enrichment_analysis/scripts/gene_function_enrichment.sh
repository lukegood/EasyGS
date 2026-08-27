#!/bin/sh

set -eu

species=""
analysis_type=""
genelist_txt=""
summary_output=""
kegg_r_script=""
go_r_script=""
summary_script=""
gene2ko_tsv=""
kegg_annotation_tsv=""
kegg_all_output=""
kegg_significant_output=""
kegg_mapped_output=""
kegg_plot_output=""
gene2go_tsv=""
go_term_tsv=""
go_all_output=""
go_significant_output=""
go_mapped_output=""
go_plot_output=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --species) species="$2"; shift 2 ;;
    --analysis-type) analysis_type="$2"; shift 2 ;;
    --genelist-txt) genelist_txt="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --kegg-r-script) kegg_r_script="$2"; shift 2 ;;
    --go-r-script) go_r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --gene2ko-tsv) gene2ko_tsv="$2"; shift 2 ;;
    --kegg-annotation-tsv) kegg_annotation_tsv="$2"; shift 2 ;;
    --kegg-all-output) kegg_all_output="$2"; shift 2 ;;
    --kegg-significant-output) kegg_significant_output="$2"; shift 2 ;;
    --kegg-mapped-output) kegg_mapped_output="$2"; shift 2 ;;
    --kegg-plot-output) kegg_plot_output="$2"; shift 2 ;;
    --gene2go-tsv) gene2go_tsv="$2"; shift 2 ;;
    --go-term-tsv) go_term_tsv="$2"; shift 2 ;;
    --go-all-output) go_all_output="$2"; shift 2 ;;
    --go-significant-output) go_significant_output="$2"; shift 2 ;;
    --go-mapped-output) go_mapped_output="$2"; shift 2 ;;
    --go-plot-output) go_plot_output="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

for required in "$species" "$analysis_type" "$genelist_txt" "$summary_output" \
  "$kegg_r_script" "$go_r_script" "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments for gene function enrichment." >&2
    exit 2
  fi
done

case "$species" in
  wheat|rice) ;;
  *) echo "Species must be wheat or rice: $species" >&2; exit 2 ;;
esac

case "$analysis_type" in
  ALL|GO|KEGG) ;;
  *) echo "Analysis type must be ALL, GO, or KEGG: $analysis_type" >&2; exit 2 ;;
esac

for tool in Rscript python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for input_file in "$genelist_txt" "$kegg_r_script" "$go_r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

missing_packages="$(
  Rscript -e "pkgs <- c('clusterProfiler','dplyr','ggplot2'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available in EasyGS_1: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$summary_output")"

if [ "$analysis_type" = "ALL" ] || [ "$analysis_type" = "KEGG" ]; then
  for required in "$gene2ko_tsv" "$kegg_annotation_tsv" "$kegg_all_output" \
    "$kegg_significant_output" "$kegg_mapped_output" "$kegg_plot_output"
  do
    if [ -z "$required" ]; then
      echo "Missing required KEGG arguments." >&2
      exit 2
    fi
  done
  for input_file in "$gene2ko_tsv" "$kegg_annotation_tsv"; do
    if [ ! -f "$input_file" ]; then
      echo "Required KEGG resource not found: $input_file" >&2
      exit 1
    fi
  done
  mkdir -p "$(dirname "$kegg_all_output")"
  mkdir -p "$(dirname "$kegg_significant_output")"
  mkdir -p "$(dirname "$kegg_mapped_output")"
  mkdir -p "$(dirname "$kegg_plot_output")"

  Rscript "$kegg_r_script" \
    --genelist-txt "$genelist_txt" \
    --gene2ko-tsv "$gene2ko_tsv" \
    --kegg-annotation-tsv "$kegg_annotation_tsv" \
    --all-output "$kegg_all_output" \
    --significant-output "$kegg_significant_output" \
    --mapped-output "$kegg_mapped_output" \
    --plot-output "$kegg_plot_output"
fi

if [ "$analysis_type" = "ALL" ] || [ "$analysis_type" = "GO" ]; then
  for required in "$gene2go_tsv" "$go_term_tsv" "$go_all_output" \
    "$go_significant_output" "$go_mapped_output" "$go_plot_output"
  do
    if [ -z "$required" ]; then
      echo "Missing required GO arguments." >&2
      exit 2
    fi
  done
  for input_file in "$gene2go_tsv" "$go_term_tsv"; do
    if [ ! -f "$input_file" ]; then
      echo "Required GO resource not found: $input_file" >&2
      exit 1
    fi
  done
  mkdir -p "$(dirname "$go_all_output")"
  mkdir -p "$(dirname "$go_significant_output")"
  mkdir -p "$(dirname "$go_mapped_output")"
  mkdir -p "$(dirname "$go_plot_output")"

  Rscript "$go_r_script" \
    --genelist-txt "$genelist_txt" \
    --gene2go-tsv "$gene2go_tsv" \
    --go-term-tsv "$go_term_tsv" \
    --all-output "$go_all_output" \
    --significant-output "$go_significant_output" \
    --mapped-output "$go_mapped_output" \
    --plot-output "$go_plot_output"
fi

set -- \
  --species "$species" \
  --analysis-type "$analysis_type" \
  --genelist-txt "$genelist_txt" \
  --summary-output "$summary_output"

if [ "$analysis_type" = "ALL" ] || [ "$analysis_type" = "KEGG" ]; then
  set -- "$@" \
    --gene2ko-tsv "$gene2ko_tsv" \
    --kegg-annotation-tsv "$kegg_annotation_tsv" \
    --kegg-all-output "$kegg_all_output" \
    --kegg-significant-output "$kegg_significant_output" \
    --kegg-mapped-output "$kegg_mapped_output" \
    --kegg-plot-output "$kegg_plot_output"
fi

if [ "$analysis_type" = "ALL" ] || [ "$analysis_type" = "GO" ]; then
  set -- "$@" \
    --gene2go-tsv "$gene2go_tsv" \
    --go-term-tsv "$go_term_tsv" \
    --go-all-output "$go_all_output" \
    --go-significant-output "$go_significant_output" \
    --go-mapped-output "$go_mapped_output" \
    --go-plot-output "$go_plot_output"
fi

python3 "$summary_script" "$@"

echo "Wheat/rice gene function enrichment completed."
echo "Species: $species"
echo "Analysis type: $analysis_type"
echo "Summary: $summary_output"
