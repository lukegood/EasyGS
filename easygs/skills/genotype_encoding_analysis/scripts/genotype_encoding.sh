#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  genotype_encoding.sh \
    (--ped-prefix <input_prefix> | --bfile <input_prefix>) \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_genotype_encoding.py>

Required tools:
  plink
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash genotype_encoding.sh ...
EOF
}

ped_prefix=""
bfile_prefix=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --ped-prefix) ped_prefix="$2"; shift 2 ;;
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$out_prefix" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

input_count=0
if [ -n "$ped_prefix" ]; then
  input_count=$((input_count + 1))
fi
if [ -n "$bfile_prefix" ]; then
  input_count=$((input_count + 1))
fi

if [ "$input_count" -ne 1 ]; then
  echo "Provide exactly one of --ped-prefix or --bfile." >&2
  exit 1
fi

for tool in plink python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

if [ -n "$ped_prefix" ]; then
  input_label="ped"
  input_path="$ped_prefix"
  plink --file "$ped_prefix" --recodeA --out "$out_prefix"
else
  input_label="bfile"
  input_path="$bfile_prefix"
  plink --bfile "$bfile_prefix" --recodeA --out "$out_prefix"
fi

python3 "$summary_script" \
  --input-label "$input_label" \
  --input-path "$input_path" \
  --raw "${out_prefix}.raw" \
  --log "${out_prefix}.log" \
  --nosex "${out_prefix}.nosex" \
  --output "$summary_output"

echo "Genotype encoding completed."
echo "Input (${input_label}): ${input_path}"
echo "Additive genotype matrix: ${out_prefix}.raw"
echo "PLINK log: ${out_prefix}.log"
echo "PLINK .nosex: ${out_prefix}.nosex"
echo "Summary file: ${summary_output}"
