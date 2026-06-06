#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  locus_subset.sh \
    --bfile <prefix> \
    --action <extract|exclude> \
    --loci-list <loci.txt> \
    --loci-input-label <label> \
    --subset-prefix <prefix> \
    --bed-prefix <prefix> \
    --summary-output <summary.txt> \
    --summary-script <summarize_locus_subset.py>

Required tools:
  plink
  python3
EOF
}

bfile_prefix=""
action=""
loci_list=""
loci_input_label=""
subset_prefix=""
bed_prefix=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --action) action="$2"; shift 2 ;;
    --loci-list) loci_list="$2"; shift 2 ;;
    --loci-input-label) loci_input_label="$2"; shift 2 ;;
    --subset-prefix) subset_prefix="$2"; shift 2 ;;
    --bed-prefix) bed_prefix="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$bfile_prefix" "$action" "$loci_list" "$loci_input_label" "$subset_prefix" "$bed_prefix" "$summary_output" "$summary_script"; do
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

mkdir -p "$(dirname "$subset_prefix")"
mkdir -p "$(dirname "$bed_prefix")"
mkdir -p "$(dirname "$summary_output")"

case "$action" in
  extract)
    plink --bfile "$bfile_prefix" --extract "$loci_list" --recode --out "$subset_prefix"
    ;;
  exclude)
    plink --bfile "$bfile_prefix" --exclude "$loci_list" --recode --out "$subset_prefix"
    ;;
  *)
    echo "Unsupported action: $action" >&2
    exit 1
    ;;
esac

plink --file "$subset_prefix" --make-bed --out "$bed_prefix"
plink --bfile "$bed_prefix" --export vcf --out "$subset_prefix"

python3 "$summary_script" \
  --action "$action" \
  --input-bfile "$bfile_prefix" \
  --loci-input-label "$loci_input_label" \
  --loci-list "$loci_list" \
  --subset-prefix "$subset_prefix" \
  --bed-prefix "$bed_prefix" \
  --output "$summary_output"

echo "Locus subset analysis completed."
echo "Action: ${action}"
echo "Subset PED prefix: ${subset_prefix}"
echo "Intermediate BED prefix: ${bed_prefix}"
echo "Exported VCF: ${subset_prefix}.vcf"
echo "Summary file: ${summary_output}"
