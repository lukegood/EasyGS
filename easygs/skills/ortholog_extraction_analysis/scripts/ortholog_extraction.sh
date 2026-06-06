#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  ortholog_extraction.sh \
    --genelist-txt <genelist.txt> \
    --ortholog-matrix-tsv <maize_ortholog_matrix.tsv> \
    --output-tsv <genelist.ortholog.tsv> \
    --summary-output <genelist.ortholog_summary.txt> \
    --summary-script <summarize_ortholog_extraction.py>

Required tools:
  grep
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash ortholog_extraction.sh ...
EOF
}

genelist_txt=""
ortholog_matrix_tsv=""
output_tsv=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --genelist-txt) genelist_txt="$2"; shift 2 ;;
    --ortholog-matrix-tsv) ortholog_matrix_tsv="$2"; shift 2 ;;
    --output-tsv) output_tsv="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$genelist_txt" \
  "$ortholog_matrix_tsv" \
  "$output_tsv" \
  "$summary_output" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in grep python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for input_file in "$genelist_txt" "$ortholog_matrix_tsv" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required input file not found: $input_file" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$output_tsv")"
mkdir -p "$(dirname "$summary_output")"

if ! grep -F -f "$genelist_txt" "$ortholog_matrix_tsv" > "$output_tsv"; then
  status=$?
  if [ "$status" -ne 1 ]; then
    echo "grep failed with exit code $status" >&2
    exit "$status"
  fi
  : > "$output_tsv"
fi

python3 "$summary_script" \
  --genelist-txt "$genelist_txt" \
  --ortholog-matrix-tsv "$ortholog_matrix_tsv" \
  --output-tsv "$output_tsv" \
  --summary-output "$summary_output"

echo "Ortholog extraction completed."
echo "Ortholog TSV: $output_tsv"
echo "Summary file: $summary_output"
