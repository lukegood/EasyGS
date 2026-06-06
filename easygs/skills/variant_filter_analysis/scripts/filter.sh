#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  filter.sh \
    --vcf <input.vcf|input.vcf.gz> \
    --out-dir <output_dir> \
    --bed-prefix <filtered> \
    --vcf-prefix <filter> \
    --mind <float> \
    --geno <float> \
    --hwe <float> \
    --maf <float> \
    --bgzip-output <0|1> \
    --tabix-index <0|1> \
    --summary-output <summary.txt> \
    --summary-script <summarize_filter.py> \
    [--link-dir <dir>]

Required tools:
  plink
  python3
  bgzip (when --bgzip-output 1)
  tabix (when --tabix-index 1)
EOF
}

vcf_file=""
out_dir=""
bed_prefix=""
vcf_prefix=""
mind=""
geno=""
hwe=""
maf=""
bgzip_output="1"
tabix_index="1"
summary_output=""
summary_script=""
link_dir=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf) vcf_file="$2"; shift 2 ;;
    --out-dir) out_dir="$2"; shift 2 ;;
    --bed-prefix) bed_prefix="$2"; shift 2 ;;
    --vcf-prefix) vcf_prefix="$2"; shift 2 ;;
    --mind) mind="$2"; shift 2 ;;
    --geno) geno="$2"; shift 2 ;;
    --hwe) hwe="$2"; shift 2 ;;
    --maf) maf="$2"; shift 2 ;;
    --bgzip-output) bgzip_output="$2"; shift 2 ;;
    --tabix-index) tabix_index="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --link-dir) link_dir="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in "$vcf_file" "$out_dir" "$bed_prefix" "$vcf_prefix" "$mind" "$geno" "$hwe" "$maf" "$summary_output" "$summary_script"; do
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

if [ "$bgzip_output" = "1" ] && ! command -v bgzip >/dev/null 2>&1; then
  echo "Required tool not found on PATH: bgzip" >&2
  exit 1
fi

if [ "$tabix_index" = "1" ] && ! command -v tabix >/dev/null 2>&1; then
  echo "Required tool not found on PATH: tabix" >&2
  exit 1
fi

mkdir -p "$out_dir"
mkdir -p "$(dirname "$summary_output")"

bed_out="${out_dir}/${bed_prefix}"
vcf_out="${out_dir}/${vcf_prefix}"

plink --vcf "$vcf_file" --mind "$mind" --geno "$geno" --hwe "$hwe" --maf "$maf" --make-bed --out "$bed_out"
plink --bfile "$bed_out" --export vcf --out "$vcf_out"

if [ "$bgzip_output" = "1" ]; then
  bgzip -f "${vcf_out}.vcf"
fi

if [ "$tabix_index" = "1" ]; then
  tabix -f -p vcf "${vcf_out}.vcf.gz"
fi

if [ -n "$link_dir" ]; then
  mkdir -p "$link_dir"
  if [ "$bgzip_output" = "1" ]; then
    ln -sfn "${vcf_out}.vcf.gz" "${link_dir}/$(basename "${vcf_out}.vcf.gz")"
  fi
  if [ "$tabix_index" = "1" ]; then
    ln -sfn "${vcf_out}.vcf.gz.tbi" "${link_dir}/$(basename "${vcf_out}.vcf.gz.tbi")"
  fi
fi

python3 "$summary_script" \
  --bed-prefix "$bed_out" \
  --vcf-gz "${vcf_out}.vcf.gz" \
  --output "$summary_output" \
  --mind "$mind" \
  --geno "$geno" \
  --hwe "$hwe" \
  --maf "$maf"

echo "Variant filtering completed."
echo "BED prefix: ${bed_out}"
echo "Filtered VCF.GZ: ${vcf_out}.vcf.gz"
echo "Summary file: ${summary_output}"
