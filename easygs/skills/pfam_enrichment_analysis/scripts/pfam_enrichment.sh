#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  pfam_enrichment.sh \
    --genelist-txt <genelist.txt> \
    --longest-cds-txt <all_maize_longest_cds.txt> \
    --proteins-tsv <all_maize_genes_proteins.fa.tsv> \
    --annotation-source <Pfam> \
    --min-count-in-candidates <5> \
    --p-adjust-method <BH> \
    --fdr-cutoff <0.05> \
    --protlist-output <protlist.txt> \
    --protlist-stranno-output <protlist.stranno.tsv> \
    --source-annotation-tsv-output <pfam_enrichment_Pfam.source.tsv> \
    --all-enrichment-csv-output <pfam_enrichment_all_pfam_enrichment.csv> \
    --sig-enrichment-csv-output <pfam_enrichment_sig_pfam.csv> \
    --summary-output <pfam_enrichment_summary.txt> \
    --r-script <run_pfam_enrichment.R> \
    --summary-script <summarize_pfam_enrichment.py> \
    [--background-protein-txt <background.txt>]

Required tools:
  Rscript
  awk
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash pfam_enrichment.sh ...
EOF
}

genelist_txt=""
longest_cds_txt=""
proteins_tsv=""
background_protein_txt=""
annotation_source=""
min_count_in_candidates=""
p_adjust_method=""
fdr_cutoff=""
protlist_output=""
protlist_stranno_output=""
source_annotation_tsv_output=""
all_enrichment_csv_output=""
sig_enrichment_csv_output=""
summary_output=""
r_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --genelist-txt) genelist_txt="$2"; shift 2 ;;
    --longest-cds-txt) longest_cds_txt="$2"; shift 2 ;;
    --proteins-tsv) proteins_tsv="$2"; shift 2 ;;
    --background-protein-txt) background_protein_txt="$2"; shift 2 ;;
    --annotation-source) annotation_source="$2"; shift 2 ;;
    --min-count-in-candidates) min_count_in_candidates="$2"; shift 2 ;;
    --p-adjust-method) p_adjust_method="$2"; shift 2 ;;
    --fdr-cutoff) fdr_cutoff="$2"; shift 2 ;;
    --protlist-output) protlist_output="$2"; shift 2 ;;
    --protlist-stranno-output) protlist_stranno_output="$2"; shift 2 ;;
    --source-annotation-tsv-output) source_annotation_tsv_output="$2"; shift 2 ;;
    --all-enrichment-csv-output) all_enrichment_csv_output="$2"; shift 2 ;;
    --sig-enrichment-csv-output) sig_enrichment_csv_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --r-script) r_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$genelist_txt" \
  "$longest_cds_txt" \
  "$proteins_tsv" \
  "$annotation_source" \
  "$min_count_in_candidates" \
  "$p_adjust_method" \
  "$fdr_cutoff" \
  "$protlist_output" \
  "$protlist_stranno_output" \
  "$source_annotation_tsv_output" \
  "$all_enrichment_csv_output" \
  "$sig_enrichment_csv_output" \
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

for tool in Rscript awk python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for input_file in "$genelist_txt" "$longest_cds_txt" "$proteins_tsv" "$r_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

if [ -n "$background_protein_txt" ] && [ ! -f "$background_protein_txt" ]; then
  echo "Background protein TXT not found: $background_protein_txt" >&2
  exit 1
fi

mkdir -p "$(dirname "$protlist_output")"
mkdir -p "$(dirname "$protlist_stranno_output")"
mkdir -p "$(dirname "$source_annotation_tsv_output")"
mkdir -p "$(dirname "$all_enrichment_csv_output")"
mkdir -p "$(dirname "$sig_enrichment_csv_output")"
mkdir -p "$(dirname "$summary_output")"

awk 'NR==FNR {ids[$1]=1; next} (($1) in ids) && NF >= 2 {print $2}' "$genelist_txt" "$longest_cds_txt" \
  | awk 'NF > 0 && !seen[$0]++' > "$protlist_output"

awk 'NR==FNR {ids[$1]=1; next} (($1) in ids)' "$protlist_output" "$proteins_tsv" > "$protlist_stranno_output"

awk -v src="$annotation_source" 'BEGIN {FS=OFS="\t"} NF >= 5 && $4 == src && $5 != "" && $5 != "-" {print $0}' \
  "$proteins_tsv" > "$source_annotation_tsv_output"

if [ -n "$background_protein_txt" ]; then
  Rscript "$r_script" \
    --protlist-txt "$protlist_output" \
    --source-annotation-tsv "$source_annotation_tsv_output" \
    --background-protein-txt "$background_protein_txt" \
    --annotation-source "$annotation_source" \
    --min-count-in-candidates "$min_count_in_candidates" \
    --p-adjust-method "$p_adjust_method" \
    --fdr-cutoff "$fdr_cutoff" \
    --all-enrichment-csv-output "$all_enrichment_csv_output" \
    --sig-enrichment-csv-output "$sig_enrichment_csv_output"
else
  Rscript "$r_script" \
    --protlist-txt "$protlist_output" \
    --source-annotation-tsv "$source_annotation_tsv_output" \
    --annotation-source "$annotation_source" \
    --min-count-in-candidates "$min_count_in_candidates" \
    --p-adjust-method "$p_adjust_method" \
    --fdr-cutoff "$fdr_cutoff" \
    --all-enrichment-csv-output "$all_enrichment_csv_output" \
    --sig-enrichment-csv-output "$sig_enrichment_csv_output"
fi

python3 "$summary_script" \
  --genelist-txt "$genelist_txt" \
  --longest-cds-txt "$longest_cds_txt" \
  --proteins-tsv "$proteins_tsv" \
  --background-protein-txt "$background_protein_txt" \
  --annotation-source "$annotation_source" \
  --min-count-in-candidates "$min_count_in_candidates" \
  --p-adjust-method "$p_adjust_method" \
  --fdr-cutoff "$fdr_cutoff" \
  --protlist-output "$protlist_output" \
  --protlist-stranno-output "$protlist_stranno_output" \
  --all-enrichment-csv-output "$all_enrichment_csv_output" \
  --sig-enrichment-csv-output "$sig_enrichment_csv_output" \
  --summary-output "$summary_output"

echo "PFAM/domain enrichment completed."
echo "protlist.txt: $protlist_output"
echo "protlist.stranno.tsv: $protlist_stranno_output"
echo "Source-filtered TSV: $source_annotation_tsv_output"
echo "All enrichment CSV: $all_enrichment_csv_output"
echo "Significant enrichment CSV: $sig_enrichment_csv_output"
echo "Summary file: $summary_output"
