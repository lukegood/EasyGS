"""Mean nucleotide-diversity analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedMeanNucleotideDiversityRun:
    """Prepared mean-nucleotide-diversity execution plan."""

    prefix: str
    command: list[str]
    sites_pi_path: Path
    output_dir: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "prefix": self.prefix,
            "sites_pi_path": str(self.sites_pi_path),
            "output_dir": str(self.output_dir),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunMeanNucleotideDiversityTool(PlinkToolBase, Tool):
    """Compute mean pi from a vcftools .sites.pi file."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="mean_nucleotide_diversity_analysis",
            default_output_subdir="mean_nucleotide_diversity",
        )
        self.script_path = self.skill_dir / "mean_nucleotide_diversity.sh"
        self.summary_script_path = self.skill_dir / "summarize_mean_nucleotide_diversity.py"

    @property
    def name(self) -> str:
        return "run_mean_nucleotide_diversity"

    @property
    def description(self) -> str:
        return (
            "Compute the average nucleotide diversity (pi) from a user-provided "
            "vcftools .sites.pi file."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sites_pi": {
                    "type": "string",
                    "description": (
                        "Required path to the user-provided nucleotide_diversity.sites.pi "
                        "file or another vcftools .sites.pi file."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/mean_nucleotide_diversity/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for the generated summary text. Defaults to 'mean_pi', "
                        "which generates <prefix>_summary.txt."
                    ),
                },
            },
            "required": ["sites_pi"],
        }

    async def execute(
        self,
        sites_pi: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                sites_pi=sites_pi,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Mean nucleotide-diversity analysis failed.\n"
                f"- Input sites.pi: {prepared.sites_pi_path}\n"
                f"- Summary file: {prepared.summary_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Mean nucleotide-diversity analysis completed.",
            f"- Input sites.pi: {prepared.sites_pi_path}",
            f"- Output dir: {prepared.output_dir}",
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
        sites_pi: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedMeanNucleotideDiversityRun:
        sites_pi_path = _resolve_path(sites_pi, self.allowed_dir)
        if not sites_pi_path.exists():
            raise ValueError(f"sites.pi file not found: {sites_pi_path}")
        if not sites_pi_path.is_file():
            raise ValueError(f"sites.pi input must be a file: {sites_pi_path}")
        if not str(sites_pi_path).endswith(".sites.pi"):
            raise ValueError(f"sites.pi input must end with .sites.pi: {sites_pi_path}")

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "mean_pi")
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        command = [
            "bash",
            str(self.script_path),
            "--sites-pi",
            str(sites_pi_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedMeanNucleotideDiversityRun(
            prefix=prefix_name,
            command=command,
            sites_pi_path=sites_pi_path,
            output_dir=output_root,
            summary_path=summary_path,
        )
