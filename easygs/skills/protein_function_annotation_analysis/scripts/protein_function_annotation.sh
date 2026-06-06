#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  protein_function_annotation.sh \
    --genelist-txt <genelist.txt> \
    --longest-cds-txt <all_maize_longest_cds.txt> \
    --proteins-tsv <all_maize_genes_proteins.fa.tsv> \
    --gene-protein-map-output <gene_protein_map.tsv> \
    --protlist-output <protlist.txt> \
    --protlist-stranno-output <protlist.stranno.tsv> \
    --annotation-tsv-output <protein_function_annotation.tsv> \
    --summary-output <protein_function_annotation_summary.txt> \
    --summary-script <summarize_protein_function_annotation.py> \
    [--annotation-source <all|Pfam|...>]

Required tools:
  awk
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash protein_function_annotation.sh ...
EOF
}

genelist_txt=""
longest_cds_txt=""
proteins_tsv=""
annotation_source="all"
gene_protein_map_output=""
protlist_output=""
protlist_stranno_output=""
annotation_tsv_output=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --genelist-txt) genelist_txt="$2"; shift 2 ;;
    --longest-cds-txt) longest_cds_txt="$2"; shift 2 ;;
    --proteins-tsv) proteins_tsv="$2"; shift 2 ;;
    --annotation-source) annotation_source="$2"; shift 2 ;;
    --gene-protein-map-output) gene_protein_map_output="$2"; shift 2 ;;
    --protlist-output) protlist_output="$2"; shift 2 ;;
    --protlist-stranno-output) protlist_stranno_output="$2"; shift 2 ;;
    --annotation-tsv-output) annotation_tsv_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$genelist_txt" \
  "$longest_cds_txt" \
  "$proteins_tsv" \
  "$gene_protein_map_output" \
  "$protlist_output" \
  "$protlist_stranno_output" \
  "$annotation_tsv_output" \
  "$summary_output" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in awk python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for input_file in "$genelist_txt" "$longest_cds_txt" "$proteins_tsv" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$gene_protein_map_output")"
mkdir -p "$(dirname "$protlist_output")"
mkdir -p "$(dirname "$protlist_stranno_output")"
mkdir -p "$(dirname "$annotation_tsv_output")"
mkdir -p "$(dirname "$summary_output")"

awk 'BEGIN {FS=OFS="\t"} NR==FNR {ids[$1]=1; next} (($1) in ids) && NF >= 2 && !seen[$1 "\t" $2]++ {print $1, $2}' \
  "$genelist_txt" "$longest_cds_txt" > "$gene_protein_map_output"

awk 'BEGIN {FS=OFS="\t"} NF >= 2 && !seen[$2]++ {print $2}' "$gene_protein_map_output" > "$protlist_output"

awk -v src="$annotation_source" 'BEGIN {FS=OFS="\t"; all=(src == "" || src == "all" || src == "ALL")} NR==FNR {ids[$1]=1; next} (($1) in ids) && (all || $4 == src)' \
  "$protlist_output" "$proteins_tsv" > "$protlist_stranno_output"

awk -v src="$annotation_source" '
  BEGIN {
    FS=OFS="\t"
    all=(src == "" || src == "all" || src == "ALL")
    print "gene_id", "protein_id", "protein_md5", "sequence_length", "analysis", "signature_accession", "signature_description", "start", "stop", "score", "status", "date", "interpro_accession", "interpro_description", "go_annotations", "pathway_annotations"
  }
  function value(i) {
    return (i <= NF && $i != "") ? $i : "-"
  }
  NR==FNR {
    if (NF >= 2 && $2 != "") {
      genes[$2] = (($2 in genes) ? genes[$2] SUBSEP $1 : $1)
    }
    next
  }
  (($1) in genes) && (all || $4 == src) {
    n = split(genes[$1], gene_ids, SUBSEP)
    for (i = 1; i <= n; i++) {
      print gene_ids[i], value(1), value(2), value(3), value(4), value(5), value(6), value(7), value(8), value(9), value(10), value(11), value(12), value(13), value(14), value(15)
    }
  }
' "$gene_protein_map_output" "$proteins_tsv" > "$annotation_tsv_output"

python3 "$summary_script" \
  --genelist-txt "$genelist_txt" \
  --longest-cds-txt "$longest_cds_txt" \
  --proteins-tsv "$proteins_tsv" \
  --annotation-source "$annotation_source" \
  --gene-protein-map-output "$gene_protein_map_output" \
  --protlist-output "$protlist_output" \
  --protlist-stranno-output "$protlist_stranno_output" \
  --annotation-tsv-output "$annotation_tsv_output" \
  --summary-output "$summary_output"

echo "Protein function annotation completed."
echo "Gene-protein map TSV: $gene_protein_map_output"
echo "protlist.txt: $protlist_output"
echo "protlist.stranno.tsv: $protlist_stranno_output"
echo "Protein function annotation TSV: $annotation_tsv_output"
echo "Summary file: $summary_output"
