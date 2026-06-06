#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  bfile_extract.sh \
    --bfile <prefix> \
    --extract-file <extract.txt> \
    --out-prefix <prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_bfile_extract.py>

Required tools:
  plink
  python3
EOF
}

bfile_prefix=""
extract_file=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --extract-file) extract_file="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$bfile_prefix" "$extract_file" "$out_prefix" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in plink python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

if [ ! -f "$extract_file" ]; then
  echo "Extract file not found: $extract_file" >&2
  exit 1
fi

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

plink --bfile "$bfile_prefix" --extract "$extract_file" --make-bed --out "$out_prefix"

python3 "$summary_script" \
  --input-bfile "$bfile_prefix" \
  --extract-file "$extract_file" \
  --out-prefix "$out_prefix" \
  --output "$summary_output"

echo "BFILE extraction completed."
echo "BED file: ${out_prefix}.bed"
echo "BIM file: ${out_prefix}.bim"
echo "FAM file: ${out_prefix}.fam"
echo "Summary file: ${summary_output}"
