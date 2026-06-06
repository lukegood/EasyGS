#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  gebv.sh \
    --grm-prefix <grm_prefix> \
    --pheno <phenotype.txt> \
    --out-prefix <output_prefix> \
    --clean-output <gebv_clean.txt> \
    --top-output <top_selection.txt> \
    --summary-output <summary.txt> \
    --summary-script <summarize_gebv.py> \
    --top-percent <integer>

Required tools:
  gcta64
  python3

Environment:
  Run inside EasyGS_2 or with:
    mamba run -n EasyGS_2 bash gebv.sh ...
EOF
}

grm_prefix=""
pheno_file=""
out_prefix=""
clean_output=""
top_output=""
summary_output=""
summary_script=""
top_percent=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --grm-prefix) grm_prefix="$2"; shift 2 ;;
    --pheno) pheno_file="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --clean-output) clean_output="$2"; shift 2 ;;
    --top-output) top_output="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --top-percent) top_percent="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$grm_prefix" \
  "$pheno_file" \
  "$out_prefix" \
  "$clean_output" \
  "$top_output" \
  "$summary_output" \
  "$summary_script" \
  "$top_percent"
do
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

if [ ! -f "${grm_prefix}.grm.bin" ] || [ ! -f "${grm_prefix}.grm.N.bin" ] || [ ! -f "${grm_prefix}.grm.id" ]; then
  echo "GRM prefix is incomplete: ${grm_prefix}" >&2
  exit 1
fi

if [ ! -f "$pheno_file" ]; then
  echo "Phenotype file not found: $pheno_file" >&2
  exit 1
fi

mkdir -p "$(dirname "$out_prefix")"
mkdir -p "$(dirname "$clean_output")"
mkdir -p "$(dirname "$top_output")"
mkdir -p "$(dirname "$summary_output")"

gcta64 --reml \
  --grm "$grm_prefix" \
  --pheno "$pheno_file" \
  --reml-pred-rand \
  --out "$out_prefix"

python3 "$summary_script" \
  --grm-prefix "$grm_prefix" \
  --pheno "$pheno_file" \
  --hsq "${out_prefix}.hsq" \
  --blp "${out_prefix}.indi.blp" \
  --log "${out_prefix}.log" \
  --clean-output "$clean_output" \
  --top-output "$top_output" \
  --summary-output "$summary_output" \
  --top-percent "$top_percent"

echo "GEBV analysis completed."
echo "GCTA hsq file: ${out_prefix}.hsq"
echo "GCTA BLP file: ${out_prefix}.indi.blp"
echo "GCTA log: ${out_prefix}.log"
echo "Clean GEBV file: ${clean_output}"
echo "Top-selection file: ${top_output}"
echo "Summary file: ${summary_output}"
