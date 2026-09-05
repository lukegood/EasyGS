"""Configurable-reference paired-end FASTQ to VCF pipeline tool."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path

_REFERENCE_FASTA_FILENAME = "Zm-B73-REFERENCE-GRAMENE-4.0.fa"
_R1_SUFFIX = "_1.fq.gz"
_R2_SUFFIX = "_2.fq.gz"
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass
class PreparedFastqToVcfRun:
    """Prepared execution plan for the paired-end FASTQ-to-VCF pipeline."""

    launcher: str
    command: list[str]
    project_id: str
    sample_ids: list[str]
    threads: int
    parallel_jobs: int
    fastq_dir: Path
    sample_sheet_path: Path | None
    reference_fasta_path: Path
    platform: str
    library: str
    min_depth: int
    min_allele_depth: int
    output_dir: Path
    qc_dir: Path
    mapping_dir: Path
    variant_calling_dir: Path
    final_output_dir: Path
    logs_dir: Path
    final_vcf_path: Path
    final_vcf_index_path: Path
    stats_path: Path
    genotypes_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "project_id": self.project_id,
            "sample_ids": list(self.sample_ids),
            "threads": self.threads,
            "parallel_jobs": self.parallel_jobs,
            "fastq_dir": str(self.fastq_dir),
            "sample_sheet_path": str(self.sample_sheet_path) if self.sample_sheet_path else "",
            "reference_fasta_path": str(self.reference_fasta_path),
            "platform": self.platform,
            "library": self.library,
            "min_depth": self.min_depth,
            "min_allele_depth": self.min_allele_depth,
            "output_dir": str(self.output_dir),
            "qc_dir": str(self.qc_dir),
            "mapping_dir": str(self.mapping_dir),
            "variant_calling_dir": str(self.variant_calling_dir),
            "final_output_dir": str(self.final_output_dir),
            "logs_dir": str(self.logs_dir),
            "final_vcf_path": str(self.final_vcf_path),
            "final_vcf_index_path": str(self.final_vcf_index_path),
            "stats_path": str(self.stats_path),
            "genotypes_path": str(self.genotypes_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }


class RunFastqToVcfTool(PlinkToolBase, Tool):
    """Run a paired-end short-read FASTQ-to-VCF workflow."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 14400):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="fastq_to_vcf_analysis",
            default_output_subdir="fastq_to_vcf",
            env_name="EasyGS_5",
        )
        self.script_path = self.skill_dir / "fastq_to_vcf.sh"
        self.filter_script_path = self.skill_dir / "filter_genotype.py"
        self.stats_script_path = self.skill_dir / "snp_stats.py"
        self.summary_script_path = self.skill_dir / "summarize_fastq_to_vcf.py"
        self.resource_dir = resolve_user_resource_path("fastq_to_vcf_analysis")
        self.default_reference_path = self.resource_dir / _REFERENCE_FASTA_FILENAME

    @property
    def name(self) -> str:
        return "run_fastq_to_vcf"

    @property
    def description(self) -> str:
        return (
            "Run a configurable-reference, diploid paired-end short-read FASTQ-to-VCF pipeline "
            "in the EasyGS_5 conda environment. The managed maize B73 v4 reference is used by "
            "default; another reference FASTA may be supplied explicitly."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "fastq_dir": {
                    "type": "string",
                    "description": (
                        "Directory containing one or more paired-end samples named "
                        "<sample_id>_1.fq.gz and <sample_id>_2.fq.gz."
                    ),
                },
                "sample_sheet": {
                    "type": "string",
                    "description": (
                        "Optional tab-separated file with sample_id, r1, and r2 columns. Relative "
                        "read paths are resolved from the sample-sheet directory. When omitted, "
                        "reads are discovered as <sample_id>_1.fq.gz and <sample_id>_2.fq.gz."
                    ),
                },
                "reference_fasta": {
                    "type": "string",
                    "description": (
                        "Optional uncompressed .fa, .fasta, or .fna reference genome. When omitted, "
                        "the managed maize B73 RefGen_v4 reference is used. Required BWA, FASTA, "
                        "and sequence-dictionary indexes are prepared in the project directory."
                    ),
                },
                "project_id": {
                    "type": "string",
                    "description": (
                        "Optional project/output directory name. Defaults to the FASTQ directory "
                        "name, for example E250143075."
                    ),
                },
                "threads": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Threads used by fastp, BWA, samtools, and GATK. Default: 10.",
                },
                "parallel_jobs": {
                    "type": "integer",
                    "minimum": 1,
                    "description": (
                        "Number of parallel per-sample GATK HaplotypeCaller jobs. Default: 10."
                    ),
                },
                "platform": {
                    "type": "string",
                    "default": "DNBSEQ",
                    "description": (
                        "SAM read-group sequencing platform, for example DNBSEQ or ILLUMINA."
                    ),
                },
                "library": {
                    "type": "string",
                    "default": "lib1",
                    "description": "Read-group library identifier. Default: lib1.",
                },
                "min_depth": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 5,
                    "description": "Minimum per-sample genotype depth; lower-depth GTs are masked.",
                },
                "min_allele_depth": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 4,
                    "description": (
                        "Minimum allele depth for every called allele in a heterozygous genotype."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional parent output directory. The project is written to "
                        "<output_dir>/<project_id>/."
                    ),
                },
            },
            "required": ["fastq_dir"],
        }

    async def execute(
        self,
        fastq_dir: str,
        sample_sheet: str | None = None,
        reference_fasta: str | None = None,
        project_id: str | None = None,
        threads: int = 10,
        parallel_jobs: int = 10,
        platform: str = "DNBSEQ",
        library: str = "lib1",
        min_depth: int = 5,
        min_allele_depth: int = 4,
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        if kwargs.get("filter_script") or kwargs.get("stats_script"):
            return (
                "Error: filter_script and stats_script are internal pipeline components and "
                "cannot be overridden through the public fastq_to_vcf_analysis interface."
            )
        try:
            prepared = await self.prepare_run(
                fastq_dir=fastq_dir,
                sample_sheet=sample_sheet,
                reference_fasta=reference_fasta,
                project_id=project_id,
                threads=threads,
                parallel_jobs=parallel_jobs,
                platform=platform,
                library=library,
                min_depth=min_depth,
                min_allele_depth=min_allele_depth,
                output_dir=output_dir,
            )
        except (PermissionError, ValueError) as exc:
            return f"Error: {exc}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: FASTQ-to-VCF analysis failed.\n"
                f"- Project: {prepared.project_id}\n"
                f"- FASTQ directory: {prepared.fastq_dir}\n"
                f"- Output directory: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "FASTQ-to-VCF analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Project: {prepared.project_id}",
            f"- Samples: {len(prepared.sample_ids)}",
            f"- FASTQ directory: {prepared.fastq_dir}",
            f"- Sample sheet: {prepared.sample_sheet_path or 'automatic filename discovery'}",
            f"- Reference FASTA: {prepared.reference_fasta_path}",
            f"- Read-group platform: {prepared.platform}",
            f"- Output directory: {prepared.output_dir}",
            f"- QC directory: {prepared.qc_dir}",
            f"- Final VCF.GZ: {prepared.final_vcf_path}",
            f"- Final VCF index: {prepared.final_vcf_index_path}",
            f"- Logs directory: {prepared.logs_dir}",
            f"- Summary file: {prepared.summary_path}",
        ]
        preview = self._read_preview(prepared.summary_path)
        if preview:
            lines.extend(["", "Summary preview:", preview])
        details = self._join_output(run_result["stdout"], run_result["stderr"])
        if details:
            lines.extend(["", details])
        return "\n".join(lines)

    async def prepare_run(
        self,
        *,
        fastq_dir: str,
        sample_sheet: str | None = None,
        reference_fasta: str | None = None,
        project_id: str | None = None,
        threads: int = 10,
        parallel_jobs: int = 10,
        platform: str = "DNBSEQ",
        library: str = "lib1",
        min_depth: int = 5,
        min_allele_depth: int = 4,
        output_dir: str | None = None,
    ) -> PreparedFastqToVcfRun:
        fastq_dir_path = self._resolve_fastq_dir(fastq_dir)
        sample_sheet_path = self._resolve_sample_sheet(sample_sheet)
        sample_ids = (
            self._read_sample_sheet(sample_sheet_path)
            if sample_sheet_path
            else self._discover_sample_pairs(fastq_dir_path)
        )
        project_id_value = self._resolve_project_id(project_id, fastq_dir_path)

        threads_value = int(threads)
        parallel_jobs_value = int(parallel_jobs)
        if threads_value < 1:
            raise ValueError("threads must be >= 1")
        if parallel_jobs_value < 1:
            raise ValueError("parallel_jobs must be >= 1")
        min_depth_value = int(min_depth)
        min_allele_depth_value = int(min_allele_depth)
        if min_depth_value < 0:
            raise ValueError("min_depth must be >= 0")
        if min_allele_depth_value < 0:
            raise ValueError("min_allele_depth must be >= 0")
        platform_value = self._resolve_read_group_value(platform, "platform")
        library_value = self._resolve_read_group_value(library, "library")

        reference_fasta_path = self._resolve_reference_fasta(reference_fasta)
        output_root = self._resolve_output_dir(output_dir)
        project_output_dir = output_root / project_id_value
        qc_dir = project_output_dir / "01-QC"
        mapping_dir = project_output_dir / "02-Mapping"
        variant_calling_dir = project_output_dir / "03-VariantCalling"
        final_output_dir = project_output_dir / "04-Output"
        logs_dir = project_output_dir / "logs"
        final_vcf_path = final_output_dir / f"{project_id_value}.vcf.gz"
        final_vcf_index_path = final_output_dir / f"{project_id_value}.vcf.gz.tbi"
        stats_path = final_output_dir / "snp_statistics.tsv"
        genotypes_path = final_output_dir / "genotypes.tsv"
        summary_path = project_output_dir / f"{project_id_value}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "genotype-filter script": self.filter_script_path,
            "SNP-statistics script": self.stats_script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        required_tools = [
            "fastp",
            "bwa",
            "samtools",
            "picard",
            "gatk",
            "bgzip",
            "tabix",
            "python3",
            "xargs",
        ]
        env_status = await self._get_environment_status(required_tools)
        if env_status["error"]:
            error = env_status["error"]
            raise ValueError(error[7:] if error.startswith("Error: ") else error)

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "bash",
            str(self.script_path),
            "--fastq-dir",
            str(fastq_dir_path),
            "--project-id",
            project_id_value,
            "--reference-fasta",
            str(reference_fasta_path),
            "--filter-script",
            str(self.filter_script_path),
            "--stats-script",
            str(self.stats_script_path),
            "--output-dir",
            str(project_output_dir),
            "--threads",
            str(threads_value),
            "--parallel-jobs",
            str(parallel_jobs_value),
            "--platform",
            platform_value,
            "--library",
            library_value,
            "--min-depth",
            str(min_depth_value),
            "--min-allele-depth",
            str(min_allele_depth_value),
            "--sample-count",
            str(len(sample_ids)),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if sample_sheet_path:
            command.extend(["--sample-sheet", str(sample_sheet_path)])

        return PreparedFastqToVcfRun(
            launcher=env_status["launcher"],
            command=command,
            project_id=project_id_value,
            sample_ids=sample_ids,
            threads=threads_value,
            parallel_jobs=parallel_jobs_value,
            fastq_dir=fastq_dir_path,
            sample_sheet_path=sample_sheet_path,
            reference_fasta_path=reference_fasta_path,
            platform=platform_value,
            library=library_value,
            min_depth=min_depth_value,
            min_allele_depth=min_allele_depth_value,
            output_dir=project_output_dir,
            qc_dir=qc_dir,
            mapping_dir=mapping_dir,
            variant_calling_dir=variant_calling_dir,
            final_output_dir=final_output_dir,
            logs_dir=logs_dir,
            final_vcf_path=final_vcf_path,
            final_vcf_index_path=final_vcf_index_path,
            stats_path=stats_path,
            genotypes_path=genotypes_path,
            summary_path=summary_path,
        )

    def _resolve_fastq_dir(self, value: str) -> Path:
        if not value:
            raise ValueError("fastq_dir is required.")
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"FASTQ directory not found: {path}")
        if not path.is_dir():
            raise ValueError(f"fastq_dir must be a directory: {path}")
        return path

    def _discover_sample_pairs(self, fastq_dir: Path) -> list[str]:
        r1_paths = sorted(fastq_dir.glob(f"*{_R1_SUFFIX}"))
        r2_paths = sorted(fastq_dir.glob(f"*{_R2_SUFFIX}"))
        if not r1_paths:
            raise ValueError(
                f"FASTQ directory does not contain any *{_R1_SUFFIX} files: {fastq_dir}"
            )

        sample_ids: list[str] = []
        paired_r2_names: set[str] = set()
        for r1_path in r1_paths:
            if not r1_path.is_file():
                continue
            sample_id = r1_path.name[: -len(_R1_SUFFIX)]
            if not _SAFE_NAME_RE.fullmatch(sample_id):
                raise ValueError(
                    "FASTQ sample IDs may contain only letters, numbers, '.', '_', and '-': "
                    f"{sample_id}"
                )
            r2_path = fastq_dir / f"{sample_id}{_R2_SUFFIX}"
            if not r2_path.is_file():
                raise ValueError(f"Missing R2 mate for {r1_path.name}: {r2_path}")
            sample_ids.append(sample_id)
            paired_r2_names.add(r2_path.name)

        orphan_r2 = [path.name for path in r2_paths if path.name not in paired_r2_names]
        if orphan_r2:
            raise ValueError(f"R2 FASTQ files are missing matching R1 mates: {', '.join(orphan_r2)}")
        if not sample_ids:
            raise ValueError(f"FASTQ directory does not contain any regular R1 files: {fastq_dir}")
        return sample_ids

    def _resolve_sample_sheet(self, value: str | None) -> Path | None:
        if not value:
            return None
        path = _resolve_path(value, self.allowed_dir)
        if not path.is_file():
            raise ValueError(f"Sample sheet not found or not a regular file: {path}")
        return path

    def _read_sample_sheet(self, path: Path) -> list[str]:
        sample_ids: list[str] = []
        seen: set[str] = set()
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            required_columns = ["sample_id", "r1", "r2"]
            if reader.fieldnames != required_columns:
                raise ValueError(
                    "Sample sheet must be a TSV containing exactly these columns in order: "
                    "sample_id, r1, r2."
                )
            for line_number, row in enumerate(reader, start=2):
                if not any((value or "").strip() for value in row.values()):
                    continue
                sample_id = (row.get("sample_id") or "").strip()
                if not _SAFE_NAME_RE.fullmatch(sample_id):
                    raise ValueError(
                        f"Invalid sample_id at sample-sheet line {line_number}: {sample_id!r}"
                    )
                if sample_id in seen:
                    raise ValueError(f"Duplicate sample_id in sample sheet: {sample_id}")
                read_paths: list[Path] = []
                for column in ("r1", "r2"):
                    raw_path = (row.get(column) or "").strip()
                    if not raw_path:
                        raise ValueError(
                            f"Missing {column} path at sample-sheet line {line_number}."
                        )
                    candidate = Path(raw_path).expanduser()
                    if not candidate.is_absolute():
                        candidate = path.parent / candidate
                    resolved = _resolve_path(str(candidate), self.allowed_dir)
                    if not resolved.is_file():
                        raise ValueError(
                            f"{column} FASTQ not found at sample-sheet line {line_number}: "
                            f"{resolved}"
                        )
                    read_paths.append(resolved)
                if read_paths[0] == read_paths[1]:
                    raise ValueError(
                        f"r1 and r2 must be different files at sample-sheet line {line_number}."
                    )
                seen.add(sample_id)
                sample_ids.append(sample_id)
        if not sample_ids:
            raise ValueError(f"Sample sheet contains no samples: {path}")
        return sample_ids

    def _resolve_project_id(self, value: str | None, fastq_dir: Path) -> str:
        candidate = (value or fastq_dir.name).strip()
        if not candidate or not _SAFE_NAME_RE.fullmatch(candidate):
            raise ValueError(
                "project_id must start with a letter or number and contain only letters, "
                "numbers, '.', '_', and '-'"
            )
        return candidate

    def _resolve_reference_fasta(self, value: str | None) -> Path:
        path = (
            _resolve_path(value, self.allowed_dir)
            if value
            else self.default_reference_path.expanduser().resolve()
        )
        if not path.is_file():
            if value:
                raise ValueError(f"Reference FASTA not found or not a regular file: {path}")
            raise ValueError(
                "Managed maize B73 RefGen_v4 FASTA not found: "
                f"{path}. Place {_REFERENCE_FASTA_FILENAME} under {self.resource_dir}, set "
                "EASYGS_RESOURCES_DIR, or provide reference_fasta explicitly."
            )
        if path.suffix.lower() not in {".fa", ".fasta", ".fna"}:
            raise ValueError(
                "reference_fasta must be an uncompressed .fa, .fasta, or .fna file: "
                f"{path}"
            )
        return path

    def _resolve_read_group_value(self, value: str, label: str) -> str:
        candidate = str(value or "").strip()
        if not _SAFE_NAME_RE.fullmatch(candidate):
            raise ValueError(
                f"{label} must start with a letter or number and contain only letters, "
                "numbers, '.', '_', and '-'"
            )
        return candidate
