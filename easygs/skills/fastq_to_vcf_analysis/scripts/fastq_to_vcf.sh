#!/bin/bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  fastq_to_vcf.sh \
    --fastq-dir <E250143075> \
    --project-id <E250143075> \
    --reference-fasta <Zm-B73-REFERENCE-GRAMENE-4.0.fa> \
    --filter-script <filter_genotype.py> \
    --stats-script <snp_stats.py> \
    --output-dir <result/E250143075> \
    --threads <10> \
    --parallel-jobs <10> \
    --summary-output <E250143075_summary.txt> \
    --summary-script <summarize_fastq_to_vcf.py>

The FASTQ directory may contain any number of paired samples named:
  <sample_id>_1.fq.gz
  <sample_id>_2.fq.gz
EOF
}

fastq_dir=""
project_id=""
reference_fasta=""
filter_script=""
stats_script=""
output_dir=""
threads=""
parallel_jobs=""
summary_output=""
summary_script=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --fastq-dir) fastq_dir="$2"; shift 2 ;;
    --project-id) project_id="$2"; shift 2 ;;
    --reference-fasta) reference_fasta="$2"; shift 2 ;;
    --filter-script) filter_script="$2"; shift 2 ;;
    --stats-script) stats_script="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --threads) threads="$2"; shift 2 ;;
    --parallel-jobs) parallel_jobs="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for required in \
  "$fastq_dir" \
  "$project_id" \
  "$reference_fasta" \
  "$filter_script" \
  "$stats_script" \
  "$output_dir" \
  "$threads" \
  "$parallel_jobs" \
  "$summary_output" \
  "$summary_script"
do
  if [ -z "$required" ]; then
    echo "Missing required arguments." >&2
    usage >&2
    exit 1
  fi
done

for tool in fastp bwa samtools picard gatk bgzip tabix python3 xargs; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Required tool not found on PATH: $tool" >&2
    exit 1
  fi
done

for required_file in "$reference_fasta" "$filter_script" "$stats_script" "$summary_script"; do
  if [ ! -f "$required_file" ]; then
    echo "Required file not found: $required_file" >&2
    exit 1
  fi
done
if [ ! -d "$fastq_dir" ]; then
  echo "FASTQ directory not found: $fastq_dir" >&2
  exit 1
fi

case "$threads" in
  ''|*[!0-9]*|0) echo "threads must be a positive integer" >&2; exit 1 ;;
esac
case "$parallel_jobs" in
  ''|*[!0-9]*|0) echo "parallel-jobs must be a positive integer" >&2; exit 1 ;;
esac

qc_dir="${output_dir}/01-QC"
mapping_dir="${output_dir}/02-Mapping"
variant_dir="${output_dir}/03-VariantCalling"
final_dir="${output_dir}/04-Output"
logs_dir="${output_dir}/logs"
mkdir -p "$qc_dir" "$mapping_dir" "$variant_dir" "$final_dir" "$logs_dir"

samples=()
for r1 in "$fastq_dir"/*_1.fq.gz; do
  [ -f "$r1" ] || continue
  filename="$(basename "$r1")"
  sample="${filename%_1.fq.gz}"
  r2="${fastq_dir}/${sample}_2.fq.gz"
  if [ ! -f "$r2" ]; then
    echo "Missing R2 mate for $r1: $r2" >&2
    exit 1
  fi
  samples+=("$sample")
done
if [ "${#samples[@]}" -eq 0 ]; then
  echo "No *_1.fq.gz files found in: $fastq_dir" >&2
  exit 1
fi

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "开始原始数据质控 (fastp)"
for sample in "${samples[@]}"; do
  log "处理样本: ${sample}"
  fastp \
    -i "${fastq_dir}/${sample}_1.fq.gz" \
    -I "${fastq_dir}/${sample}_2.fq.gz" \
    -o "${qc_dir}/${sample}_R1.clean.fastq.gz" \
    -O "${qc_dir}/${sample}_R2.clean.fastq.gz" \
    -n 10 -q 20 -u 40 -w "$threads" \
    --html "${qc_dir}/${sample}_fastp.html" \
    --json "${qc_dir}/${sample}_fastp.json" \
    2> "${logs_dir}/${sample}_fastp.log"
done

log "开始序列比对 (BWA)"
for sample in "${samples[@]}"; do
  log "比对样本: ${sample}"
  bwa mem \
    -t "$threads" \
    -R "@RG\tID:${sample}\tSM:${sample}\tLB:lib1\tPL:MGIT7" \
    "$reference_fasta" \
    "${qc_dir}/${sample}_R1.clean.fastq.gz" \
    "${qc_dir}/${sample}_R2.clean.fastq.gz" \
    2> "${logs_dir}/${sample}_bwa.log" \
    | samtools view -@ "$threads" -bS - > "${mapping_dir}/${sample}.bam"

  log "排序BAM文件: ${sample}"
  samtools sort \
    -@ "$threads" \
    -o "${mapping_dir}/${sample}.sorted.bam" \
    "${mapping_dir}/${sample}.bam"
  samtools index -@ "$threads" "${mapping_dir}/${sample}.sorted.bam"
  rm -f "${mapping_dir}/${sample}.bam"
done

log "开始标记重复序列 (picard)"
for sample in "${samples[@]}"; do
  log "处理样本: ${sample}"
  picard MarkDuplicates \
    I="${mapping_dir}/${sample}.sorted.bam" \
    O="${mapping_dir}/${sample}.dedup.bam" \
    M="${mapping_dir}/${sample}_duplicates_metrics.txt" \
    REMOVE_DUPLICATES=true \
    MAX_RECORDS_IN_RAM=5000000 \
    2> "${logs_dir}/${sample}_markdup.log"
  samtools index "${mapping_dir}/${sample}.dedup.bam"
done

call_variants() {
  sample="$1"
  gatk HaplotypeCaller \
    -R "$REFERENCE_FASTA" \
    -I "${MAPPING_DIR}/${sample}.dedup.bam" \
    -O "${VARIANT_DIR}/${sample}.g.vcf.gz" \
    --native-pair-hmm-threads "$THREADS" \
    -ERC GVCF \
    > "${LOGS_DIR}/${sample}_haplotype.log" 2>&1

  python3 "$FILTER_SCRIPT" \
    "${VARIANT_DIR}/${sample}.g.vcf.gz" \
    "${VARIANT_DIR}/${sample}.filter.vcf" \
    > "${LOGS_DIR}/${sample}_filter.log" 2>&1
}
export -f call_variants
export REFERENCE_FASTA="$reference_fasta"
export MAPPING_DIR="$mapping_dir"
export VARIANT_DIR="$variant_dir"
export LOGS_DIR="$logs_dir"
export FILTER_SCRIPT="$filter_script"
export THREADS="$threads"

log "开始变异检测 (GATK HaplotypeCaller)"
printf '%s\n' "${samples[@]}" \
  | xargs -r -n 1 -P "$parallel_jobs" bash -c 'set -euo pipefail; call_variants "$1"' _

log "合并 gVCF"
variants=()
for gvcf in "$variant_dir"/*.g.vcf.gz; do
  variants+=(--variant "$gvcf")
done
gatk CombineGVCFs \
  -R "$reference_fasta" \
  "${variants[@]}" \
  -O "${variant_dir}/combined.g.vcf.gz" \
  > "${logs_dir}/combine_gvcfs.log" 2>&1

log "联合基因型判断"
gatk GenotypeGVCFs \
  -R "$reference_fasta" \
  -V "${variant_dir}/combined.g.vcf.gz" \
  -O "${variant_dir}/final.vcf.gz" \
  > "${logs_dir}/genotype_gvcfs.log" 2>&1

tabix -f -p vcf "${variant_dir}/final.vcf.gz" \
  > "${logs_dir}/tabix_final.log" 2>&1

log "过滤基因型"
python3 "$filter_script" \
  "${variant_dir}/final.vcf.gz" \
  "${variant_dir}/final.filtered.vcf" \
  > "${logs_dir}/filter_genotype.log" 2>&1

log "压缩过滤后的VCF"
bgzip -f "${variant_dir}/final.filtered.vcf" \
  > "${logs_dir}/bgzip_filtered.log" 2>&1
tabix -f -p vcf "${variant_dir}/final.filtered.vcf.gz" \
  > "${logs_dir}/tabix_filtered.log" 2>&1

log "统计SNP"
python3 "$stats_script" \
  "${variant_dir}/final.filtered.vcf.gz" \
  "${final_dir}/snp_statistics.tsv" \
  "${final_dir}/genotypes.tsv" \
  > "${logs_dir}/snp_statistics.log" 2>&1

log "整理最终结果"
cp "${variant_dir}/final.filtered.vcf.gz" "${final_dir}/${project_id}.vcf.gz"
cp "${variant_dir}/final.filtered.vcf.gz.tbi" "${final_dir}/${project_id}.vcf.gz.tbi"

python3 "$summary_script" \
  --project-id "$project_id" \
  --fastq-dir "$fastq_dir" \
  --reference-fasta "$reference_fasta" \
  --output-dir "$output_dir" \
  --threads "$threads" \
  --parallel-jobs "$parallel_jobs" \
  --output "$summary_output"

log "所有分析完成"
echo "Final VCF.GZ: ${final_dir}/${project_id}.vcf.gz"
echo "Summary file: ${summary_output}"
