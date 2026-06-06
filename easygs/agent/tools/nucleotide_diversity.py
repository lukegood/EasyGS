"""Nucleotide-diversity (pi) analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

def _format_window_label(window_size: int) -> str:
    if window_size % 1_000_000 == 0:
        return f"{window_size // 1_000_000}mb"
    if window_size % 1_000 == 0:
        return f"{window_size // 1_000}kb"
    return f"{window_size}bp"


@dataclass
class PreparedNucleotideDiversityRun:
    """Prepared vcftools nucleotide-diversity execution plan."""

    launcher: str
    mode: str
    prefix: str
    command: list[str]
    vcf_path: Path
    output_dir: Path
    output_prefix_path: Path
    result_path: Path
    result_label: str
    log_path: Path
    summary_path: Path
    window_size: int | None = None
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "mode": self.mode,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "result_path": str(self.result_path),
            "result_label": self.result_label,
            "log_path": str(self.log_path),
            "summary_path": str(self.summary_path),
            "window_size": self.window_size,
            "notes": list(self.notes),
        }



class RunNucleotideDiversityTool(PlinkToolBase, Tool):
    """Run vcftools site-pi or window-pi analysis for a VCF/VCF.GZ input."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="nucleotide_diversity_analysis",
            default_output_subdir="nucleotide_diversity",
        )
        self.script_path = self.skill_dir / "nucleotide_diversity.sh"
        self.summary_script_path = self.skill_dir / "summarize_nucleotide_diversity.py"

    @property
    def name(self) -> str:
        return "run_nucleotide_diversity"

    @property
    def description(self) -> str:
        return (
            "Run vcftools nucleotide-diversity analysis on a VCF/VCF.GZ file. Supports "
            "whole-genome site-pi mode and window-pi mode, and validates the EasyGS_2 "
            "environment before execution."
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
                "mode": {
                    "type": "string",
                    "enum": ["site", "window"],
                    "description": (
                        "Analysis mode. Use 'site' for vcftools --site-pi, or 'window' for "
                        "vcftools --window-pi. Defaults to 'site' unless window_size is given."
                    ),
                },
                "window_size": {
                    "type": "integer",
                    "description": (
                        "Window size for mode='window'. Defaults to 100000 when window mode "
                        "is requested without an explicit size."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/nucleotide_diversity/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for vcftools outputs. Defaults to 'nucleotide_diversity' "
                        "for site mode or 'window_pi_100kb' for the default window mode."
                    ),
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        mode: str | None = None,
        window_size: int | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                mode=mode,
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
                "Error: Nucleotide-diversity analysis failed.\n"
                f"- Mode: {prepared.mode}\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Nucleotide-diversity analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Mode: {prepared.mode}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- {prepared.result_label}: {prepared.result_path}",
            f"- vcftools log: {prepared.log_path}",
            f"- Summary file: {prepared.summary_path}",
        ]
        if prepared.window_size is not None:
            lines.append(f"- Window size: {prepared.window_size}")
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
        mode: str | None = None,
        window_size: int | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedNucleotideDiversityRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)

        parsed_window_size: int | None = None
        if window_size is not None:
            try:
                parsed_window_size = int(window_size)
            except (TypeError, ValueError) as exc:
                raise ValueError("window_size must be a positive integer.") from exc
            if parsed_window_size <= 0:
                raise ValueError("window_size must be a positive integer.")

        analysis_mode = (mode or "").strip().lower()
        if not analysis_mode:
            analysis_mode = "window" if parsed_window_size is not None else "site"
        if analysis_mode not in {"site", "window"}:
            raise ValueError("mode must be either 'site' or 'window'.")

        if analysis_mode == "site":
            if parsed_window_size is not None:
                raise ValueError("window_size can only be used when mode='window'.")
            default_prefix = "nucleotide_diversity"
            result_path_suffix = ".sites.pi"
            result_label = "Site PI file"
            actual_window_size = None
        else:
            actual_window_size = parsed_window_size or 100000
            default_prefix = f"window_pi_{_format_window_label(actual_window_size)}"
            result_path_suffix = ".windowed.pi"
            result_label = "Windowed PI file"

        prefix_name = self._normalize_prefix_name(prefix, default_prefix)
        output_prefix_path = output_root / prefix_name
        result_path = output_root / f"{prefix_name}{result_path_suffix}"
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
            "--mode",
            analysis_mode,
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if actual_window_size is not None:
            command.extend(["--window-size", str(actual_window_size)])

        return PreparedNucleotideDiversityRun(
            launcher=env_status["launcher"],
            mode=analysis_mode,
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            result_path=result_path,
            result_label=result_label,
            log_path=log_path,
            summary_path=summary_path,
            window_size=actual_window_size,
        )
