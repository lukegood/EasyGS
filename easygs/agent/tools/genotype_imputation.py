"""Beagle-based genotype imputation tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_software_path


@dataclass
class PreparedGenotypeImputationRun:
    """Prepared Beagle genotype-imputation execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    jar_path: Path
    output_dir: Path
    output_prefix_path: Path
    imputed_vcf_gz_path: Path
    log_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "jar_path": str(self.jar_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "imputed_vcf_gz_path": str(self.imputed_vcf_gz_path),
            "log_path": str(self.log_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunGenotypeImputationTool(PlinkToolBase, Tool):
    """Run Beagle genotype imputation for a VCF/VCF.GZ input."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="genotype_imputation_analysis",
            default_output_subdir="genotype_imputation",
        )
        self.script_path = self.skill_dir / "genotype_imputation.sh"
        self.summary_script_path = self.skill_dir / "summarize_genotype_imputation.py"
        self.jar_path = resolve_software_path("beagle.29Oct24.c8e.jar")

    @property
    def name(self) -> str:
        return "run_genotype_imputation"

    @property
    def description(self) -> str:
        return (
            "Run Beagle genotype imputation on a VCF/VCF.GZ input using the bundled "
            "beagle.29Oct24.c8e.jar resource. The tool validates the EasyGS_2 environment first."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {
                    "type": "string",
                    "description": "User-provided path to the input VCF or VCF.GZ file.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/genotype_imputation/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for Beagle outputs. Defaults to 'tianchong'. "
                        "Generates <prefix>.vcf.gz and <prefix>.log."
                    ),
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Genotype imputation failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Beagle jar: {prepared.jar_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Genotype imputation completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Beagle jar: {prepared.jar_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Output prefix: {prepared.output_prefix_path}",
            f"- Imputed VCF.GZ: {prepared.imputed_vcf_gz_path}",
            f"- Beagle log: {prepared.log_path}",
            f"- Summary file: {prepared.summary_path}",
        ]
        if prepared.notes:
            lines.extend(f"- Note: {note}" for note in prepared.notes)
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
        vcf: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedGenotypeImputationRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "tianchong")
        output_prefix_path = output_root / prefix_name
        imputed_vcf_gz_path = output_root / f"{prefix_name}.vcf.gz"
        log_path = output_root / f"{prefix_name}.log"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "VCF": vcf_path,
            "Beagle jar": self.jar_path,
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["java", "python3"])
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
            "--vcf",
            str(vcf_path),
            "--jar",
            str(self.jar_path),
            "--output-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedGenotypeImputationRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            jar_path=self.jar_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            imputed_vcf_gz_path=imputed_vcf_gz_path,
            log_path=log_path,
            summary_path=summary_path,
        )
