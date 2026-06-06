#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  region_r2.sh \
    --bfile <input_prefix> \
    --chr <chromosome> \
    --from-bp <start_bp> \
    --to-bp <end_bp> \
    --ld-window <int> \
    [--ld-window-kb <int>] \
    --ld-window-r2 <float> \
    --out-prefix <output_prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_region_r2.py>

Required tools:
  plink
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash region_r2.sh ...
EOF
}

bfile_prefix=""
chromosome=""
from_bp=""
to_bp=""
ld_window=""
ld_window_kb=""
ld_window_r2=""
out_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --chr) chromosome="$2"; shift 2 ;;
    --from-bp) from_bp="$2"; shift 2 ;;
    --to-bp) to_bp="$2"; shift 2 ;;
    --ld-window) ld_window="$2"; shift 2 ;;
    --ld-window-kb) ld_window_kb="$2"; shift 2 ;;
    --ld-window-r2) ld_window_r2="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [ -z "$bfile_prefix" ] || [ -z "$chromosome" ] || [ -z "$from_bp" ] || [ -z "$to_bp" ] || [ -z "$ld_window" ] || [ -z "$ld_window_r2" ] || [ -z "$out_prefix" ] || [ -z "$summary_output" ] || [ -z "$summary_script" ]; then
  echo "Missing required arguments." >&2
  usage >&2
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

if [ -n "$ld_window_kb" ]; then
  plink \
    --bfile "$bfile_prefix" \
    --r2 \
    --chr "$chromosome" \
    --from-bp "$from_bp" \
    --to-bp "$to_bp" \
    --ld-window-kb "$ld_window_kb" \
    --ld-window "$ld_window" \
    --ld-window-r2 "$ld_window_r2" \
    --out "$out_prefix"

  python3 "$summary_script" \
    --input-bfile "$bfile_prefix" \
    --chromosome "$chromosome" \
    --from-bp "$from_bp" \
    --to-bp "$to_bp" \
    --ld-window "$ld_window" \
    --ld-window-kb "$ld_window_kb" \
    --ld-window-r2 "$ld_window_r2" \
    --ld "${out_prefix}.ld" \
    --log "${out_prefix}.log" \
    --output "$summary_output"
else
  plink \
    --bfile "$bfile_prefix" \
    --r2 \
    --chr "$chromosome" \
    --from-bp "$from_bp" \
    --to-bp "$to_bp" \
    --ld-window "$ld_window" \
    --ld-window-r2 "$ld_window_r2" \
    --out "$out_prefix"

  python3 "$summary_script" \
    --input-bfile "$bfile_prefix" \
    --chromosome "$chromosome" \
    --from-bp "$from_bp" \
    --to-bp "$to_bp" \
    --ld-window "$ld_window" \
    --ld-window-r2 "$ld_window_r2" \
    --ld "${out_prefix}.ld" \
    --log "${out_prefix}.log" \
    --output "$summary_output"
fi

echo "Regional R2 analysis completed."
echo "LD file: ${out_prefix}.ld"
echo "PLINK log: ${out_prefix}.log"
echo "PLINK .nosex: ${out_prefix}.nosex"
echo "Summary file: ${summary_output}"
