"""Phenotype BLUP analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedPhenotypeBlupRun:
    """Prepared execution plan for phenotype BLUP analysis."""

    launcher: str
    prefix: str
    command: list[str]
    phenotype_csv_path: Path
    output_dir: Path
    result_csv_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "output_dir": str(self.output_dir),
            "result_csv_path": str(self.result_csv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunPhenotypeBlupTool(PlinkToolBase, Tool):
    """Compute BLUP values from a multi-environment phenotype CSV."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="phenotype_blup_analysis",
            default_output_subdir="phenotype_blup",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "phenotype_blup.sh"
        self.r_script_path = self.skill_dir / "run_phenotype_blup.R"
        self.summary_script_path = self.skill_dir / "summarize_phenotype_blup.py"

    @property
    def name(self) -> str:
        return "run_phenotype_blup"

    @property
    def description(self) -> str:
        return (
            "Compute phenotype BLUP values from a multi-environment phenotype CSV by fitting "
            "a mixed model with line as a random effect and environment as a fixed effect."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Input multi-environment phenotype CSV in wide format. The first column "
                        "must be LINE_ID, followed by one column per environment. Example:\n"
                        "LINE_ID,CQ2012,DHN2011,GX2011,HB2011,HB2012,HN2012,SC2011,YN2011,YN2012\n"
                        "04K5686_X_Mo17,275.8,254.6,235.2,232.2,264.6,288.4,240.25,242,213\n"
                        "04K5686_X_Zheng58,222,229.4,218,214.4,224.63,241.2,216.25,201.33,194.5\n"
                        "04K5702_X_Mo17,247.5,245.5,188.75,206.75,257.3,297.75,207,215,211.2\n"
                        "05W002_X_Mo17,268,278.6,240,238.25,263.8,290.5,246,271.67,240.4"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/phenotype_blup/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for outputs. Defaults to a name derived from the input file, "
                        "for example 9地区株高.csv -> 9地区下株高BLUP值."
                    ),
                },
            },
            "required": ["phenotype_csv"],
        }

    async def execute(
        self,
        phenotype_csv: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                phenotype_csv=phenotype_csv,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Phenotype BLUP analysis failed.\n"
                f"- Input CSV: {prepared.phenotype_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Phenotype BLUP analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input CSV: {prepared.phenotype_csv_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- BLUP CSV: {prepared.result_csv_path}",
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
        phenotype_csv: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedPhenotypeBlupRun:
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, self._default_prefix_from_input(phenotype_csv_path))
        result_csv_path = output_root / f"{prefix_name}.csv"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "R script": self.r_script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["Rscript", "python3"])
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
            "--input-csv",
            str(phenotype_csv_path),
            "--output-csv",
            str(result_csv_path),
            "--summary-output",
            str(summary_path),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedPhenotypeBlupRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            phenotype_csv_path=phenotype_csv_path,
            output_dir=output_root,
            result_csv_path=result_csv_path,
            summary_path=summary_path,
        )

    def _resolve_csv_file(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"Input CSV not found: {path}")
        if not path.is_file():
            raise ValueError(f"Input phenotype CSV must be a file: {path}")
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Input phenotype CSV must end with .csv: {path}")
        return path

    def _default_prefix_from_input(self, path: Path) -> str:
        stem = path.stem.strip()
        if not stem:
            return "表型BLUP值"
        if "地区下" not in stem and "地区" in stem:
            stem = stem.replace("地区", "地区下", 1)
        if not stem.endswith("BLUP值"):
            stem = f"{stem}BLUP值"
        return stem
