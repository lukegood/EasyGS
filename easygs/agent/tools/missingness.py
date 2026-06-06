"""Standalone PLINK missingness analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedMissingnessRun:
    """Prepared PLINK missingness execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    output_dir: Path
    output_prefix: Path
    imiss_path: Path
    lmiss_path: Path
    summary_path: Path
    sample_threshold: float
    variant_threshold: float
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "output_dir": str(self.output_dir),
            "output_prefix": str(self.output_prefix),
            "imiss_path": str(self.imiss_path),
            "lmiss_path": str(self.lmiss_path),
            "summary_path": str(self.summary_path),
            "sample_threshold": self.sample_threshold,
            "variant_threshold": self.variant_threshold,
            "notes": list(self.notes),
        }



class RunMissingnessTool(PlinkToolBase, Tool):
    """Run PLINK missingness analysis and generate a summary report."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="missingness_analysis",
            default_output_subdir="missingness",
        )
        self.script_path = self.skill_dir / "missingness.sh"
        self.summary_script_path = self.skill_dir / "summarize_missingness.py"

    @property
    def name(self) -> str:
        return "run_missingness"

    @property
    def description(self) -> str:
        return (
            "Run PLINK missingness analysis on a VCF file and generate summary text for "
            "sample- and variant-level missingness using the EasyGS_2 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {"type": "string", "description": "User-provided path to the input VCF or VCF.GZ file."},
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/missingness/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": "Optional PLINK output prefix basename. Defaults to 'missingness'.",
                },
                "sample_missing_alert_threshold": {
                    "type": "number",
                    "description": "Threshold used to flag high-missingness samples in the summary.",
                },
                "variant_missing_alert_threshold": {
                    "type": "number",
                    "description": "Threshold used to flag high-missingness variants in the summary.",
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        output_dir: str | None = None,
        prefix: str = "missingness",
        sample_missing_alert_threshold: float = 0.05,
        variant_missing_alert_threshold: float = 0.05,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                output_dir=output_dir,
                prefix=prefix,
                sample_missing_alert_threshold=sample_missing_alert_threshold,
                variant_missing_alert_threshold=variant_missing_alert_threshold,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Missingness analysis failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Output prefix: {prepared.output_prefix}\n"
                f"- Summary file: {prepared.summary_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Missingness analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- VCF: {prepared.vcf_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Sample missingness file: {prepared.imiss_path}",
            f"- Variant missingness file: {prepared.lmiss_path}",
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
        prefix: str = "missingness",
        sample_missing_alert_threshold: float = 0.05,
        variant_missing_alert_threshold: float = 0.05,
    ) -> PreparedMissingnessRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)
        output_prefix = output_root / (prefix or "missingness")
        summary_path = output_root / f"{output_prefix.name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["plink"])
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
            str(output_prefix),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--sample-threshold",
            str(sample_missing_alert_threshold),
            "--variant-threshold",
            str(variant_missing_alert_threshold),
        ]
        return PreparedMissingnessRun(
            launcher=env_status["launcher"],
            prefix=output_prefix.name,
            command=command,
            vcf_path=vcf_path,
            output_dir=output_root,
            output_prefix=output_prefix,
            imiss_path=output_prefix.with_suffix(".imiss"),
            lmiss_path=output_prefix.with_suffix(".lmiss"),
            summary_path=summary_path,
            sample_threshold=sample_missing_alert_threshold,
            variant_threshold=variant_missing_alert_threshold,
        )
