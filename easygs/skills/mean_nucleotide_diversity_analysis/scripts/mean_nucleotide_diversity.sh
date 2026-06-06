#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  mean_nucleotide_diversity.sh \
    --sites-pi <input.sites.pi> \
    --summary-output <summary.txt> \
    --summary-script <summarize_mean_nucleotide_diversity.py>

Required tools:
  python3
EOF
}

sites_pi=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --sites-pi) sites_pi="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$sites_pi" "$summary_output" "$summary_script"; do
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

if [ ! -f "$sites_pi" ]; then
  echo "sites.pi file not found: $sites_pi" >&2
  exit 1
fi

case "$sites_pi" in
  *.sites.pi) ;;
  *)
    echo "sites.pi input must end with .sites.pi: $sites_pi" >&2
    exit 1
    ;;
esac

mkdir -p "$(dirname "$summary_output")"

python3 "$summary_script" \
  --sites-pi "$sites_pi" \
  --output "$summary_output"

echo "Mean nucleotide-diversity analysis completed."
echo "Input sites.pi: ${sites_pi}"
echo "Summary file: ${summary_output}"
