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
id_sort="${tmp_dir}/id_sort.txt"
pheno="${tmp_dir}/pheno.txt"
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

if [ -n "$line_list" ]; then
  awk 'NR==FNR {keep[$1]=1; next} FNR==1 {print; next} ($1 in keep) {print}' "$line_list" "$pheno_file" > "$pheno"
else
  cp "$pheno_file" "$pheno"
fi

#依据grm亲缘关系矩阵文件中的grm.id文件中材料顺序对表型文件排序
awk '{print $1}' "${grm_dir}/${prefix}.grm.id" > "$id_sort"
awk '
  NR==FNR {
    if (FNR == 1) {
      header = $0
      next
    }
    rows[$1] = $0
    next
  }
  ($1 in rows) {
    ordered[++count] = rows[$1]
  }
  END {
    if (header == "") {
      exit 1
    }
    print header
    for (i = 1; i <= count; i++) {
      print ordered[i]
    }
  }
' "$pheno" "$id_sort" > "$pheno_sort"

if [ "$(wc -l < "$pheno_sort")" -le 1 ]; then
  echo "No phenotype rows remained after matching and sorting sample IDs." >&2
  exit 1
fi

#计算遗传力
gcta64 --reml --pheno "$pheno_sort" --grm "${grm_dir}/${prefix}" --out "${result_dir}/${prefix}"

echo "Heritability analysis completed."
echo "Results saved to: ${result_dir}"
echo "Result prefix: ${result_dir}/${prefix}"
