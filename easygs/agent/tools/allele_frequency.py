"""Allele-frequency and polymorphic-site analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedAlleleFrequencyRun:
    """Prepared vcftools allele-frequency execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    output_dir: Path
    output_prefix_path: Path
    frq_path: Path
    log_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "frq_path": str(self.frq_path),
            "log_path": str(self.log_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunAlleleFrequencyTool(PlinkToolBase, Tool):
    """Run vcftools allele-frequency analysis and summarize polymorphic-site proportion."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="allele_frequency_analysis",
            default_output_subdir="allele_frequency",
        )
        self.script_path = self.skill_dir / "allele_frequency.sh"
        self.summary_script_path = self.skill_dir / "summarize_allele_frequency.py"

    @property
    def name(self) -> str:
        return "run_allele_frequency"

    @property
    def description(self) -> str:
        return (
            "Run vcftools allele-frequency analysis on a VCF/VCF.GZ file and summarize the "
            "polymorphic-site proportion using the EasyGS_2 environment."
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
                        "workspace/default_results/allele_frequency/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for vcftools outputs. Defaults to 'allele_freq'. "
                        "Generates <prefix>.frq and <prefix>.log."
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
                "Error: Allele-frequency analysis failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Allele-frequency analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Frequency file: {prepared.frq_path}",
            f"- vcftools log: {prepared.log_path}",
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
        vcf: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedAlleleFrequencyRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "allele_freq")
        output_prefix_path = output_root / prefix_name
        frq_path = output_root / f"{prefix_name}.frq"
        log_path = output_root / f"{prefix_name}.log"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["vcftools", "python3"])
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
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedAlleleFrequencyRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            frq_path=frq_path,
            log_path=log_path,
            summary_path=summary_path,
        )
