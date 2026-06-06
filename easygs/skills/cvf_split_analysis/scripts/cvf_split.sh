#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  cvf_split.sh \
    --list-txt <materials.txt> \
    --k <10> \
    --seed <42> \
    --sample-column <ID> \
    --cv-column <cv_1> \
    --output-csv <cvf.csv> \
    --summary-output <summary.txt> \
    --run-script <run_cvf_split.py> \
    --summary-script <summarize_cvf_split.py>

Required tools:
  python3

Environment:
  Run inside EasyGS_3 or with:
    mamba run -n EasyGS_3 bash cvf_split.sh ...
EOF
}

list_txt=""
k=""
seed=""
sample_column=""
cv_column=""
output_csv=""
summary_output=""
run_script=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --list-txt) list_txt="$2"; shift 2 ;;
    --k) k="$2"; shift 2 ;;
    --seed) seed="$2"; shift 2 ;;
    --sample-column) sample_column="$2"; shift 2 ;;
    --cv-column) cv_column="$2"; shift 2 ;;
    --output-csv) output_csv="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --run-script) run_script="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$list_txt" \
  "$k" \
  "$seed" \
  "$sample_column" \
  "$cv_column" \
  "$output_csv" \
  "$summary_output" \
  "$run_script" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "Required tool not found on PATH: python3" >&2
  exit 1
fi

for input_file in "$list_txt" "$run_script" "$summary_script"; do
  if [ ! -f "$input_file" ]; then
    echo "Required file not found: $input_file" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$output_csv")"
mkdir -p "$(dirname "$summary_output")"

python3 "$run_script" \
  --list-txt "$list_txt" \
  --k "$k" \
  --seed "$seed" \
  --sample-column "$sample_column" \
  --cv-column "$cv_column" \
  --output-csv "$output_csv"

python3 "$summary_script" \
  --list-txt "$list_txt" \
  --k "$k" \
  --seed "$seed" \
  --sample-column "$sample_column" \
  --cv-column "$cv_column" \
  --output-csv "$output_csv" \
  --summary-output "$summary_output"

echo "CVF split completed."
echo "CVF CSV: $output_csv"
echo "Summary file: $summary_output"
