"""Maize paired-end FASTQ to VCF pipeline tool."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path

_REFERENCE_FASTA_FILENAME = "Zm-B73-REFERENCE-GRAMENE-4.0.fa"
_REFERENCE_RESOURCE_FILENAMES = (
    _REFERENCE_FASTA_FILENAME,
    f"{_REFERENCE_FASTA_FILENAME}.amb",
    f"{_REFERENCE_FASTA_FILENAME}.ann",
    f"{_REFERENCE_FASTA_FILENAME}.bwt",
    f"{_REFERENCE_FASTA_FILENAME}.pac",
    f"{_REFERENCE_FASTA_FILENAME}.sa",
    f"{_REFERENCE_FASTA_FILENAME}.fai",
    "Zm-B73-REFERENCE-GRAMENE-4.0.dict",
)
_R1_SUFFIX = "_1.fq.gz"
_R2_SUFFIX = "_2.fq.gz"
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass
class PreparedFastqToVcfRun:
    """Prepared execution plan for the maize FASTQ-to-VCF pipeline."""

    launcher: str
    command: list[str]
    project_id: str
    sample_ids: list[str]
    threads: int
    parallel_jobs: int
    fastq_dir: Path
    reference_fasta_path: Path
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
            "reference_fasta_path": str(self.reference_fasta_path),
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
    """Run the existing maize paired-end FASTQ-to-VCF workflow."""

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
        self.reference_resource_paths = {
            filename: self.resource_dir / filename
            for filename in _REFERENCE_RESOURCE_FILENAMES
        }

    @property
    def name(self) -> str:
        return "run_fastq_to_vcf"

    @property
    def description(self) -> str:
        return (
            "Run the maize B73 v4 paired-end FASTQ-to-VCF pipeline in the EasyGS_5 conda "
            "environment. The input directory may contain any number of matched *_1.fq.gz "
            "and *_2.fq.gz sample pairs."
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
        project_id: str | None = None,
        threads: int = 10,
        parallel_jobs: int = 10,
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        if kwargs.get("reference_fasta") or kwargs.get("filter_script") or kwargs.get(
            "stats_script"
        ):
            return (
                "Error: reference and helper-script paths are not public parameters for "
                "fastq_to_vcf_analysis. EasyGS uses its managed B73 v4 resources and bundled "
                "scripts."
            )
        try:
            prepared = await self.prepare_run(
                fastq_dir=fastq_dir,
                project_id=project_id,
                threads=threads,
                parallel_jobs=parallel_jobs,
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
            f"- Reference FASTA: {prepared.reference_fasta_path}",
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
        project_id: str | None = None,
        threads: int = 10,
        parallel_jobs: int = 10,
        output_dir: str | None = None,
    ) -> PreparedFastqToVcfRun:
        fastq_dir_path = self._resolve_fastq_dir(fastq_dir)
        sample_ids = self._discover_sample_pairs(fastq_dir_path)
        project_id_value = self._resolve_project_id(project_id, fastq_dir_path)

        threads_value = int(threads)
        parallel_jobs_value = int(parallel_jobs)
        if threads_value < 1:
            raise ValueError("threads must be >= 1")
        if parallel_jobs_value < 1:
            raise ValueError("parallel_jobs must be >= 1")

        reference_fasta_path = self._resolve_reference_resources()
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
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedFastqToVcfRun(
            launcher=env_status["launcher"],
            command=command,
            project_id=project_id_value,
            sample_ids=sample_ids,
            threads=threads_value,
            parallel_jobs=parallel_jobs_value,
            fastq_dir=fastq_dir_path,
            reference_fasta_path=reference_fasta_path,
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

    def _resolve_project_id(self, value: str | None, fastq_dir: Path) -> str:
        candidate = (value or fastq_dir.name).strip()
        if not candidate or not _SAFE_NAME_RE.fullmatch(candidate):
            raise ValueError(
                "project_id must start with a letter or number and contain only letters, "
                "numbers, '.', '_', and '-'"
            )
        return candidate

    def _resolve_reference_resources(self) -> Path:
        missing = [
            str(path)
            for path in self.reference_resource_paths.values()
            if not path.is_file()
        ]
        if missing:
            missing_block = "\n".join(missing)
            raise ValueError(
                "Missing required resources for fastq_to_vcf_analysis:\n"
                f"{missing_block}\n\n"
                f"Place the B73 v4 FASTA and indexes under {self.resource_dir}. Set "
                "EASYGS_RESOURCES_DIR to use a different resource root."
            )
        return self.reference_resource_paths[_REFERENCE_FASTA_FILENAME]
