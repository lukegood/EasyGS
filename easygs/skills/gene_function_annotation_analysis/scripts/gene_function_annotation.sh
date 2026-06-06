#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  gene_function_annotation.sh \
    --genelist-txt <genelist.txt> \
    --entrez-map-csv <built-in_entrez_Zm_gene_v4.csv> \
    --gene-column <gene_name> \
    --entrez-column <ENTREZID> \
    --annotationhub-id <AH119718> \
    --kegg-organism <zma> \
    --go-ontology <ALL> \
    --kegg-pvalue-threshold <0.1> \
    --go-pvalue-threshold <0.05> \
    --kegg-txt-output <KEGG_Enrichment_Results.txt> \
    --kegg-png-output <KEGG_Enrichment_Results.png> \
    --go-txt-output <GO_Enrichment_Results.txt> \
    --go-png-output <GO_Enrichment_Results.png> \
    --mapping-summary-output <mapping_summary.tsv> \
    --summary-output <gene_function_annotation_summary.txt> \
    --r-script <run_gene_function_annotation.R> \
    --summary-script <summarize_gene_function_annotation.py>

Required tools:
  Rscript
  python3

Required R packages:
  AnnotationHub
  clusterProfiler
  ggplot2
  dplyr

Environment:
  Run inside EasyGS_1 or with:
    mamba run -n EasyGS_1 bash gene_function_annotation.sh ...
EOF
}

genelist_txt=""
entrez_map_csv=""
gene_column=""
entrez_column=""
annotationhub_id=""
kegg_organism=""
go_ontology=""
kegg_pvalue_threshold=""
go_pvalue_threshold=""
kegg_txt_output=""
kegg_png_output=""
go_txt_output=""
go_png_output=""
mapping_summary_output=""
summary_output=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --genelist-txt) genelist_txt="$2"; shift 2 ;;
    --entrez-map-csv) entrez_map_csv="$2"; shift 2 ;;
    --gene-column) gene_column="$2"; shift 2 ;;
    --entrez-column) entrez_column="$2"; shift 2 ;;
    --annotationhub-id) annotationhub_id="$2"; shift 2 ;;
    --kegg-organism) kegg_organism="$2"; shift 2 ;;
    --go-ontology) go_ontology="$2"; shift 2 ;;
    --kegg-pvalue-threshold) kegg_pvalue_threshold="$2"; shift 2 ;;
    --go-pvalue-threshold) go_pvalue_threshold="$2"; shift 2 ;;
    --kegg-txt-output) kegg_txt_output="$2"; shift 2 ;;
    --kegg-png-output) kegg_png_output="$2"; shift 2 ;;
    --go-txt-output) go_txt_output="$2"; shift 2 ;;
    --go-png-output) go_png_output="$2"; shift 2 ;;
    --mapping-summary-output) mapping_summary_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$genelist_txt" \
  "$entrez_map_csv" \
  "$gene_column" \
  "$entrez_column" \
  "$annotationhub_id" \
  "$kegg_organism" \
  "$go_ontology" \
  "$kegg_pvalue_threshold" \
  "$go_pvalue_threshold" \
  "$kegg_txt_output" \
  "$kegg_png_output" \
  "$go_txt_output" \
  "$go_png_output" \
  "$mapping_summary_output" \
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

for input_file in "$genelist_txt" "$entrez_map_csv" "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

missing_packages="$(
  Rscript -e "pkgs <- c('AnnotationHub','clusterProfiler','ggplot2','dplyr'); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) cat(paste(missing, collapse=', '))" 2>/dev/null || true
)"
if [ -n "$missing_packages" ]; then
  echo "Required R packages not available: $missing_packages" >&2
  exit 1
fi

mkdir -p "$(dirname "$kegg_txt_output")"
mkdir -p "$(dirname "$kegg_png_output")"
mkdir -p "$(dirname "$go_txt_output")"
mkdir -p "$(dirname "$go_png_output")"
mkdir -p "$(dirname "$mapping_summary_output")"
mkdir -p "$(dirname "$summary_output")"

Rscript "$r_script" \
  --genelist-txt "$genelist_txt" \
  --entrez-map-csv "$entrez_map_csv" \
  --gene-column "$gene_column" \
  --entrez-column "$entrez_column" \
  --annotationhub-id "$annotationhub_id" \
  --kegg-organism "$kegg_organism" \
  --go-ontology "$go_ontology" \
  --kegg-pvalue-threshold "$kegg_pvalue_threshold" \
  --go-pvalue-threshold "$go_pvalue_threshold" \
  --kegg-txt-output "$kegg_txt_output" \
  --kegg-png-output "$kegg_png_output" \
  --go-txt-output "$go_txt_output" \
  --go-png-output "$go_png_output" \
  --mapping-summary-output "$mapping_summary_output"

python3 "$summary_script" \
  --genelist-txt "$genelist_txt" \
  --entrez-map-csv "$entrez_map_csv" \
  --gene-column "$gene_column" \
  --entrez-column "$entrez_column" \
  --annotationhub-id "$annotationhub_id" \
  --kegg-organism "$kegg_organism" \
  --go-ontology "$go_ontology" \
  --kegg-pvalue-threshold "$kegg_pvalue_threshold" \
  --go-pvalue-threshold "$go_pvalue_threshold" \
  --kegg-txt-output "$kegg_txt_output" \
  --kegg-png-output "$kegg_png_output" \
  --go-txt-output "$go_txt_output" \
  --go-png-output "$go_png_output" \
  --mapping-summary-output "$mapping_summary_output" \
  --summary-output "$summary_output"

echo "Gene function annotation completed."
echo "KEGG TXT: $kegg_txt_output"
echo "KEGG PNG: $kegg_png_output"
echo "GO TXT: $go_txt_output"
echo "GO PNG: $go_png_output"
echo "Summary file: $summary_output"
