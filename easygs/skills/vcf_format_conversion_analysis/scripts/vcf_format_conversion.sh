#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  vcf_format_conversion.sh \
    (--vcf <input.vcf|input.vcf.gz> | --bfile <prefix> | --ped-prefix <prefix>) \
    --out-prefix <output_prefix> \
    --target-format <bed|ped|vcf> \
    --summary-output <summary.txt> \
    --summary-script <summarize_conversion.py> \
    --double-id <0|1> \
    --allow-extra-chr <0|1>

Required tools:
  plink
  python3
EOF
}

vcf_file=""
bfile_prefix=""
ped_prefix=""
out_prefix=""
target_format=""
summary_output=""
summary_script=""
double_id="1"
allow_extra_chr="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --bfile) bfile_prefix="$2"; shift 2 ;;
    --ped-prefix) ped_prefix="$2"; shift 2 ;;
    --out-prefix) out_prefix="$2"; shift 2 ;;
    --target-format) target_format="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --double-id) double_id="$2"; shift 2 ;;
    --allow-extra-chr) allow_extra_chr="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$out_prefix" "$target_format" "$summary_output" "$summary_script"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

input_count=0
if [ -n "$vcf_file" ]; then
  input_count=$((input_count + 1))
fi
if [ -n "$bfile_prefix" ]; then
  input_count=$((input_count + 1))
fi
if [ -n "$ped_prefix" ]; then
  input_count=$((input_count + 1))
fi

if [ "$input_count" -ne 1 ]; then
  echo "Provide exactly one of --vcf, --bfile, or --ped-prefix." >&2
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

case "$target_format" in
  bed)
    if [ -n "$vcf_file" ]; then
      if [ "$double_id" = "1" ]; then
        plink --vcf "$vcf_file" --double-id --make-bed --out "$out_prefix"
      else
        plink --vcf "$vcf_file" --make-bed --out "$out_prefix"
      fi
      input_label="vcf"
      input_path="$vcf_file"
    elif [ -n "$ped_prefix" ]; then
      plink --file "$ped_prefix" --make-bed --out "$out_prefix"
      input_label="ped"
      input_path="$ped_prefix"
    else
      echo "Target format 'bed' requires --vcf or --ped-prefix input." >&2
      exit 1
    fi
    ;;
  ped)
    if [ -z "$vcf_file" ]; then
      echo "Target format 'ped' requires --vcf input." >&2
      exit 1
    fi
    if [ "$allow_extra_chr" = "1" ]; then
      plink --vcf "$vcf_file" --allow-extra-chr --recode --out "$out_prefix"
    else
      plink --vcf "$vcf_file" --recode --out "$out_prefix"
    fi
    input_label="vcf"
    input_path="$vcf_file"
    ;;
  vcf)
    if [ -z "$bfile_prefix" ]; then
      echo "Target format 'vcf' requires --bfile input." >&2
      exit 1
    fi
    plink --bfile "$bfile_prefix" --export vcf --out "$out_prefix"
    input_label="bfile"
    input_path="$bfile_prefix"
    ;;
  *)
    echo "Unsupported target format: $target_format" >&2
    exit 1
    ;;
esac

python3 "$summary_script" \
  --input-label "$input_label" \
  --input-path "$input_path" \
  --out-prefix "$out_prefix" \
  --target-format "$target_format" \
  --output "$summary_output" \
  --double-id "$double_id" \
  --allow-extra-chr "$allow_extra_chr"

echo "VCF format conversion completed."
echo "Target format: ${target_format}"
echo "Output prefix: ${out_prefix}"
echo "Summary file: ${summary_output}"
