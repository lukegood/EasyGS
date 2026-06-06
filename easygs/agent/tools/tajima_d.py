"""Tajima's D analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedTajimaDRun:
    """Prepared vcftools Tajima's D execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    output_dir: Path
    output_prefix_path: Path
    result_path: Path
    log_path: Path
    summary_path: Path
    window_size: int
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "result_path": str(self.result_path),
            "log_path": str(self.log_path),
            "summary_path": str(self.summary_path),
            "window_size": self.window_size,
            "notes": list(self.notes),
        }



class RunTajimaDTool(PlinkToolBase, Tool):
    """Run vcftools Tajima's D analysis for a VCF/VCF.GZ input."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="tajima_d_analysis",
            default_output_subdir="tajima_d",
        )
        self.script_path = self.skill_dir / "tajima_d.sh"
        self.summary_script_path = self.skill_dir / "summarize_tajima_d.py"

    @property
    def name(self) -> str:
        return "run_tajima_d"

    @property
    def description(self) -> str:
        return (
            "Run vcftools Tajima's D analysis on a VCF/VCF.GZ file using a configurable "
            "window size. The tool validates the EasyGS_2 environment before execution."
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
                "window_size": {
                    "type": "integer",
                    "description": "Window size for vcftools --TajimaD. Defaults to 10000.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/tajima_d/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for vcftools outputs. Defaults to 'tajima_d'. Generates "
                        "<prefix>.Tajima.D and <prefix>.log."
                    ),
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        window_size: int | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                window_size=window_size,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Tajima's D analysis failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Window size: {prepared.window_size}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Tajima's D analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Window size: {prepared.window_size}",
            f"- Output dir: {prepared.output_dir}",
            f"- Tajima's D file: {prepared.result_path}",
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
        window_size: int | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedTajimaDRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)

        if window_size is None:
            parsed_window_size = 10000
        else:
            try:
                parsed_window_size = int(window_size)
            except (TypeError, ValueError) as exc:
                raise ValueError("window_size must be a positive integer.") from exc
        if parsed_window_size <= 0:
            raise ValueError("window_size must be a positive integer.")

        prefix_name = self._normalize_prefix_name(prefix, "tajima_d")
        output_prefix_path = output_root / prefix_name
        result_path = output_root / f"{prefix_name}.Tajima.D"
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
            "--window-size",
            str(parsed_window_size),
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedTajimaDRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            result_path=result_path,
            log_path=log_path,
            summary_path=summary_path,
            window_size=parsed_window_size,
        )
