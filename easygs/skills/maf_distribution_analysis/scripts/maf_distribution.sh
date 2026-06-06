#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  maf_distribution.sh \
    --bfile <input_prefix> \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_maf_distribution.py>

Required tools:
  plink
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash maf_distribution.sh ...
EOF
}

bfile_prefix=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$bfile_prefix" "$out_prefix" "$summary_output" "$summary_script"; do
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

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

plink --bfile "$bfile_prefix" --freq --out "$out_prefix"

python3 "$summary_script" \
  --input-bfile "$bfile_prefix" \
  --frq "${out_prefix}.frq" \
  --log "${out_prefix}.log" \
  --output "$summary_output"

echo "MAF distribution analysis completed."
echo "PLINK .nosex: ${out_prefix}.nosex"
echo "Frequency file: ${out_prefix}.frq"
echo "PLINK log: ${out_prefix}.log"
echo "Summary file: ${summary_output}"
