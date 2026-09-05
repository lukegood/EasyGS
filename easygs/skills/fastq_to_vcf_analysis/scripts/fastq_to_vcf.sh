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
    --platform <DNBSEQ> \
    --library <lib1> \
    --min-depth <5> \
    --min-allele-depth <4> \
    --sample-count <1> \
    --summary-output <E250143075_summary.txt> \
    --summary-script <summarize_fastq_to_vcf.py> \
    [--sample-sheet <samples.tsv>]

Without --sample-sheet, the FASTQ directory may contain any number of paired samples named:
  <sample_id>_1.fq.gz
  <sample_id>_2.fq.gz

A sample sheet is a tab-separated file with this header:
  sample_id<TAB>r1<TAB>r2
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
platform=""
library=""
min_depth=""
min_allele_depth=""
sample_count=""
summary_output=""
summary_script=""
sample_sheet=""

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
    --platform) platform="$2"; shift 2 ;;
    --library) library="$2"; shift 2 ;;
    --min-depth) min_depth="$2"; shift 2 ;;
    --min-allele-depth) min_allele_depth="$2"; shift 2 ;;
    --sample-count) sample_count="$2"; shift 2 ;;
    --summary-output) summary_output="$2"; shift 2 ;;
    --summary-script) summary_script="$2"; shift 2 ;;
    --sample-sheet) sample_sheet="$2"; shift 2 ;;
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
  "$platform" \
  "$library" \
  "$min_depth" \
  "$min_allele_depth" \
  "$sample_count" \
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
if [ -n "$sample_sheet" ] && [ ! -f "$sample_sheet" ]; then
  echo "Sample sheet not found: $sample_sheet" >&2
  exit 1
fi

case "$threads" in
  ''|*[!0-9]*|0) echo "threads must be a positive integer" >&2; exit 1 ;;
esac
case "$parallel_jobs" in
  ''|*[!0-9]*|0) echo "parallel-jobs must be a positive integer" >&2; exit 1 ;;
esac
case "$min_depth" in
  ''|*[!0-9]*) echo "min-depth must be a non-negative integer" >&2; exit 1 ;;
esac
case "$min_allele_depth" in
  ''|*[!0-9]*) echo "min-allele-depth must be a non-negative integer" >&2; exit 1 ;;
esac
case "$sample_count" in
  ''|*[!0-9]*|0) echo "sample-count must be a positive integer" >&2; exit 1 ;;
esac
if [[ ! "$platform" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "platform contains unsupported characters: $platform" >&2
  exit 1
fi
if [[ ! "$library" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "library contains unsupported characters: $library" >&2
  exit 1
fi

reference_dir="${output_dir}/00-Reference"
qc_dir="${output_dir}/01-QC"
mapping_dir="${output_dir}/02-Mapping"
variant_dir="${output_dir}/03-VariantCalling"
final_dir="${output_dir}/04-Output"
logs_dir="${output_dir}/logs"
mkdir -p "$reference_dir" "$qc_dir" "$mapping_dir" "$variant_dir" "$final_dir" "$logs_dir"

samples=()
r1_files=()
r2_files=()

if [ -n "$sample_sheet" ]; then
  IFS=$'\t' read -r sample_header r1_header r2_header extra_header < "$sample_sheet" || true
  sample_header="${sample_header%$'\r'}"
  r1_header="${r1_header%$'\r'}"
  r2_header="${r2_header%$'\r'}"
  if [ "$sample_header" != "sample_id" ] || [ "$r1_header" != "r1" ] || \
     [ "$r2_header" != "r2" ] || [ -n "${extra_header:-}" ]; then
    echo "Sample sheet must contain exactly these tab-separated columns: sample_id, r1, r2" >&2
    exit 1
  fi
  sample_sheet_dir="$(cd "$(dirname "$sample_sheet")" && pwd -P)"
  declare -A seen_samples=()
  line_number=1
  while IFS=$'\t' read -r sample r1 r2 extra || [ -n "${sample}${r1}${r2}${extra:-}" ]; do
    line_number=$((line_number + 1))
    sample="${sample%$'\r'}"
    r1="${r1%$'\r'}"
    r2="${r2%$'\r'}"
    if [ -z "$sample" ] && [ -z "$r1" ] && [ -z "$r2" ]; then
      continue
    fi
    if [ -z "$sample" ] || [ -z "$r1" ] || [ -z "$r2" ] || [ -n "${extra:-}" ]; then
      echo "Invalid sample-sheet row at line $line_number" >&2
      exit 1
    fi
    if [[ ! "$sample" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
      echo "Invalid sample ID at sample-sheet line $line_number: $sample" >&2
      exit 1
    fi
    if [ -n "${seen_samples[$sample]:-}" ]; then
      echo "Duplicate sample ID in sample sheet: $sample" >&2
      exit 1
    fi
    seen_samples["$sample"]=1
    if [[ "$r1" != /* ]]; then r1="${sample_sheet_dir}/${r1}"; fi
    if [[ "$r2" != /* ]]; then r2="${sample_sheet_dir}/${r2}"; fi
    if [ ! -f "$r1" ] || [ ! -f "$r2" ]; then
      echo "FASTQ file missing at sample-sheet line $line_number: $r1 or $r2" >&2
      exit 1
    fi
    samples+=("$sample")
    r1_files+=("$r1")
    r2_files+=("$r2")
  done < <(tail -n +2 "$sample_sheet")
else
  for r1 in "$fastq_dir"/*_1.fq.gz; do
    [ -f "$r1" ] || continue
    filename="$(basename "$r1")"
    sample="${filename%_1.fq.gz}"
    if [[ ! "$sample" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
      echo "Invalid sample ID discovered from FASTQ filename: $sample" >&2
      exit 1
    fi
    r2="${fastq_dir}/${sample}_2.fq.gz"
    if [ ! -f "$r2" ]; then
      echo "Missing R2 mate for $r1: $r2" >&2
      exit 1
    fi
    samples+=("$sample")
    r1_files+=("$r1")
    r2_files+=("$r2")
  done
fi
if [ "${#samples[@]}" -eq 0 ]; then
  echo "No paired FASTQ samples were found" >&2
  exit 1
fi
if [ "${#samples[@]}" -ne "$sample_count" ]; then
  echo "Validated sample count changed before execution: expected $sample_count, found ${#samples[@]}" >&2
  exit 1
fi

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

source_reference="$(readlink -f "$reference_fasta")"
reference_identity="${source_reference}|$(stat -c '%s|%y' "$source_reference")"
reference_marker="${reference_dir}/.source_path"
if [ -f "$reference_marker" ]; then
  previous_reference="$(<"$reference_marker")"
  if [ "$previous_reference" != "$reference_identity" ]; then
    echo "Output directory was prepared with a different reference: $previous_reference" >&2
    echo "Use a different project ID or output directory for $reference_identity" >&2
    exit 1
  fi
else
  printf '%s\n' "$reference_identity" > "$reference_marker"
fi

reference_name="$(basename "$source_reference")"
prepared_reference="${reference_dir}/${reference_name}"
if [ ! -e "$prepared_reference" ] && [ ! -L "$prepared_reference" ]; then
  ln -s "$source_reference" "$prepared_reference"
elif [ "$(readlink -f "$prepared_reference")" != "$source_reference" ]; then
  echo "Prepared reference path points to a different file: $prepared_reference" >&2
  exit 1
fi

bwa_source_indexes_current=true
for suffix in amb ann bwt pac sa; do
  source_index="${source_reference}.${suffix}"
  if [ ! -f "$source_index" ] || [ "$source_reference" -nt "$source_index" ]; then
    bwa_source_indexes_current=false
  fi
done
if $bwa_source_indexes_current; then
  for suffix in amb ann bwt pac sa; do
    source_index="${source_reference}.${suffix}"
    prepared_index="${prepared_reference}.${suffix}"
    if [ ! -e "$prepared_index" ] && [ ! -L "$prepared_index" ]; then
      ln -s "$source_index" "$prepared_index"
    fi
  done
fi
source_fai="${source_reference}.fai"
prepared_fai="${prepared_reference}.fai"
if [ -f "$source_fai" ] && [ ! "$source_reference" -nt "$source_fai" ] && \
   [ ! -e "$prepared_fai" ] && [ ! -L "$prepared_fai" ]; then
  ln -s "$source_fai" "$prepared_fai"
fi
source_dict="${source_reference%.*}.dict"
prepared_dict="${prepared_reference%.*}.dict"
if [ -f "$source_dict" ] && [ ! "$source_reference" -nt "$source_dict" ] && \
   [ ! -e "$prepared_dict" ] && [ ! -L "$prepared_dict" ]; then
  ln -s "$source_dict" "$prepared_dict"
fi

log "准备参考基因组索引"
if [ ! -f "${prepared_reference}.amb" ] || [ ! -f "${prepared_reference}.ann" ] || \
   [ ! -f "${prepared_reference}.bwt" ] || [ ! -f "${prepared_reference}.pac" ] || \
   [ ! -f "${prepared_reference}.sa" ]; then
  bwa index "$prepared_reference" > "${logs_dir}/reference_bwa_index.log" 2>&1
fi
if [ ! -f "${prepared_reference}.fai" ]; then
  samtools faidx "$prepared_reference" > "${logs_dir}/reference_faidx.log" 2>&1
fi
if [ ! -f "$prepared_dict" ]; then
  picard CreateSequenceDictionary \
    R="$prepared_reference" \
    O="$prepared_dict" \
    > "${logs_dir}/reference_dictionary.log" 2>&1
fi
reference_fasta="$prepared_reference"

log "开始原始数据质控 (fastp)"
for index in "${!samples[@]}"; do
  sample="${samples[$index]}"
  log "处理样本: ${sample}"
  fastp \
    -i "${r1_files[$index]}" \
    -I "${r2_files[$index]}" \
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
    -R "@RG\tID:${sample}\tSM:${sample}\tLB:${library}\tPL:${platform}" \
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

}
export -f call_variants
export REFERENCE_FASTA="$reference_fasta"
export MAPPING_DIR="$mapping_dir"
export VARIANT_DIR="$variant_dir"
export LOGS_DIR="$logs_dir"
export THREADS="$threads"

log "开始变异检测 (GATK HaplotypeCaller)"
printf '%s\n' "${samples[@]}" \
  | xargs -r -n 1 -P "$parallel_jobs" bash -c 'set -euo pipefail; call_variants "$1"' _

log "合并 gVCF"
variants=()
for sample in "${samples[@]}"; do
  gvcf="${variant_dir}/${sample}.g.vcf.gz"
  if [ ! -s "$gvcf" ]; then
    echo "Expected gVCF not found or empty: $gvcf" >&2
    exit 1
  fi
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
  --min-depth "$min_depth" \
  --min-allele-depth "$min_allele_depth" \
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
  --sample-count "$sample_count" \
  --sample-sheet "$sample_sheet" \
  --reference-fasta "$source_reference" \
  --prepared-reference "$reference_fasta" \
  --platform "$platform" \
  --library "$library" \
  --min-depth "$min_depth" \
  --min-allele-depth "$min_allele_depth" \
  --output-dir "$output_dir" \
  --threads "$threads" \
  --parallel-jobs "$parallel_jobs" \
  --output "$summary_output"

log "所有分析完成"
echo "Final VCF.GZ: ${final_dir}/${project_id}.vcf.gz"
echo "Summary file: ${summary_output}"
