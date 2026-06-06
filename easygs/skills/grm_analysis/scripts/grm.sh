#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  grm.sh \
    --bfile <prefix> \
    --out-prefix <prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_grm.py>

Required tools:
  gcta64
  python3
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

for tool in gcta64 python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$summary_output")"

gcta64 --bfile "$bfile_prefix" --make-grm --out "$out_prefix"

python3 "$summary_script" \
  --input-bfile "$bfile_prefix" \
  --out-prefix "$out_prefix" \
  --output "$summary_output"

echo "GRM construction completed."
echo "GRM bin: ${out_prefix}.grm.bin"
echo "GRM id: ${out_prefix}.grm.id"
echo "GRM N bin: ${out_prefix}.grm.N.bin"
echo "GCTA log: ${out_prefix}.log"
echo "Summary file: ${summary_output}"
