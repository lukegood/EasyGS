#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage:
  heritability.sh \
    --vcf <input.vcf> \
    --pheno <phenotype_file> \
    [--keep <sample_list.txt>] \
    --prefix <output_prefix> \
    --bed-dir <bed_dir> \
    --grm-dir <grm_dir> \
    --result-dir <result_dir>

Required tools:
  vcftools
  plink
  gcta64

Notes:
  - Run this script inside the EasyGS_2 conda environment or with:
      mamba run -n EasyGS_2 bash heritability.sh ...
  - The phenotype file must have a header row.
EOF
}

#该脚本作用：
#可选地按照材料列表从所有材料vcf文件中提取指定材料vcf
#将vcf转为二进制格式
#依据二进制基因型文件构建grm亲缘关系矩阵
#按照材料列表从所有材料表型文件中提取指定材料表型
#依据grm亲缘关系矩阵文件中的grm.id文件中材料顺序对表型文件排序
#利用gcta计算遗传力

#输入
vcf_file=""
pheno_file=""
line_list=""
prefix=""

#输出
bed_dir=""
grm_dir=""
result_dir=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vcf)
      vcf_file="$2"
      shift 2
      ;;
    --pheno)
      pheno_file="$2"
      shift 2
      ;;
    --keep)
      line_list="$2"
      shift 2
      ;;
    --prefix)
      prefix="$2"
      shift 2
      ;;
    --bed-dir)
      bed_dir="$2"
      shift 2
      ;;
    --grm-dir)
      grm_dir="$2"
      shift 2
      ;;
    --result-dir)
      result_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

for required in "$vcf_file" "$pheno_file" "$prefix" "$bed_dir" "$grm_dir" "$result_dir"; do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in vcftools plink gcta64; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

if [ ! -f "$vcf_file" ]; then
  echo "VCF file not found: $vcf_file" >&2
  exit 1
fi

if [ ! -f "$pheno_file" ]; then
  echo "Phenotype file not found: $pheno_file" >&2
  exit 1
fi

if [ -n "$line_list" ] && [ ! -f "$line_list" ]; then
  echo "Sample list not found: $line_list" >&2
  exit 1
fi

# ——自动创建输出目录——
for d in "$bed_dir" "$grm_dir" "$result_dir"; do
  mkdir -p "$d"
done

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/easygs-heritability.XXXXXX")
pheno_sort="${tmp_dir}/pheno_sort.txt"
vcf_prefix="${tmp_dir}/${prefix}"

cleanup() {
  rm -rf "$tmp_dir"
}

trap cleanup EXIT

if [ -n "$line_list" ]; then
  case "$vcf_file" in
    *.vcf.gz)
      vcftools --gzvcf "$vcf_file" --keep "$line_list" --recode --out "$vcf_prefix"
      ;;
    *.vcf)
      vcftools --vcf "$vcf_file" --keep "$line_list" --recode --out "$vcf_prefix"
      ;;
    *)
      echo "VCF input must end with .vcf or .vcf.gz: $vcf_file" >&2
      exit 1
      ;;
  esac
  plink --vcf "${vcf_prefix}.recode.vcf" --double-id --make-bed --out "${bed_dir}/${prefix}"
else
  plink --vcf "$vcf_file" --double-id --make-bed --out "${bed_dir}/${prefix}"
fi

#利用bed、bim、fam文件构建grm矩阵
gcta64 --bfile "${bed_dir}/${prefix}" --make-grm-bin --out "${grm_dir}/${prefix}"

#依据 grm.id 中的 FID+IID 顺序对表型排序。
#GCTA 的 --pheno 输入不保留标题行。
awk '
  NR==FNR {
    if (FNR == 1) next
    rows[$1 SUBSEP $2] = $0
    next
  }
  (($1 SUBSEP $2) in rows) {
    print rows[$1 SUBSEP $2]
  }
' "$pheno_file" "${grm_dir}/${prefix}.grm.id" > "$pheno_sort"

phenotype_count=$(awk 'NR > 1 && NF > 0 {count++} END {print count + 0}' "$pheno_file")
grm_count=$(awk 'NF > 0 {count++} END {print count + 0}' "${grm_dir}/${prefix}.grm.id")
matched_count=$(awk 'NF > 0 {count++} END {print count + 0}' "$pheno_sort")

echo "Heritability sample alignment: phenotype=${phenotype_count}, GRM=${grm_count}, common=${matched_count}"

if [ "$matched_count" -eq 0 ]; then
  echo "No samples are shared by the phenotype file and GRM when matching exact FID/IID pairs." >&2
  echo "Sample alignment: phenotype=${phenotype_count}, GRM=${grm_count}, common=${matched_count}" >&2
  exit 1
fi

#计算遗传力
result_prefix="${result_dir}/${prefix}"
result_hsq="${result_prefix}.hsq"
result_log="${result_prefix}.log"
rm -f "$result_hsq" "$result_log"

if ! gcta64 --reml --pheno "$pheno_sort" --grm "${grm_dir}/${prefix}" --out "$result_prefix"; then
  echo "GCTA REML failed after sample alignment: phenotype=${phenotype_count}, GRM=${grm_count}, common=${matched_count}." >&2
  if [ -f "$result_log" ]; then
    echo "GCTA result log tail:" >&2
    tail -n 40 "$result_log" >&2
  fi
  exit 1
fi

if [ ! -s "$result_hsq" ] || ! awk '$1 == "V(G)/Vp" && NF >= 3 {found=1} END {exit !found}' "$result_hsq"; then
  echo "GCTA REML exited without a valid heritability result: ${result_hsq}" >&2
  echo "Sample alignment: phenotype=${phenotype_count}, GRM=${grm_count}, common=${matched_count}" >&2
  if [ -f "$result_log" ]; then
    echo "GCTA result log tail:" >&2
    tail -n 40 "$result_log" >&2
  fi
  exit 1
fi

echo "Heritability analysis completed."
echo "Results saved to: ${result_dir}"
echo "Result prefix: ${result_dir}/${prefix}"
