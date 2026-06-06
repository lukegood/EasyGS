"""Variance decomposition analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedVarianceDecompositionRun:
    """Prepared execution plan for variance decomposition analysis."""

    launcher: str
    genotype_column: str
    environment_column: str
    phenotype_column: str
    command: list[str]
    phenotype_csv_path: Path
    output_dir: Path
    result_csv_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "genotype_column": self.genotype_column,
            "environment_column": self.environment_column,
            "phenotype_column": self.phenotype_column,
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "output_dir": str(self.output_dir),
            "result_csv_path": str(self.result_csv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunVarianceDecompositionTool(PlinkToolBase, Tool):
    """Decompose phenotype variance into genotype, environment, and residual components."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="variance_decomposition_analysis",
            default_output_subdir="variance_decomposition",
            env_name="EasyGS_3",
        )
        self.script_path = self.skill_dir / "variance_decomposition.sh"
        self.r_script_path = self.skill_dir / "run_variance_decomposition.R"
        self.summary_script_path = self.skill_dir / "summarize_variance_decomposition.py"

    @property
    def name(self) -> str:
        return "run_variance_decomposition"

    @property
    def description(self) -> str:
        return (
            "Compute genotype, environment, and residual variance-component percentages from "
            "a long-format phenotype CSV using lme4/lmerTest in EasyGS_3."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Input long-format phenotype CSV. The default expected columns are "
                        "LINE, location, and PH. Example:\n"
                        "LINE,location,PH\n"
                        "04K5686_X_Mo17,CQ2012,275.8\n"
                        "04K5686_X_Mo17,DHN2011,254.6\n"
                        "04K5686_X_Mo17,GX2011,235.2\n"
                        "04K5686_X_Mo17,HB2011,232.2"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/variance_decomposition/."
                    ),
                },
                "genotype_column": {
                    "type": "string",
                    "description": "Genotype/line column name. Defaults to 'LINE'.",
                },
                "environment_column": {
                    "type": "string",
                    "description": "Environment/location column name. Defaults to 'location'.",
                },
                "phenotype_column": {
                    "type": "string",
                    "description": "Phenotype value column name. Defaults to 'PH'.",
                },
            },
            "required": ["phenotype_csv"],
        }

    async def execute(
        self,
        phenotype_csv: str,
        output_dir: str | None = None,
        genotype_column: str | None = None,
        environment_column: str | None = None,
        phenotype_column: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                phenotype_csv=phenotype_csv,
                output_dir=output_dir,
                genotype_column=genotype_column,
                environment_column=environment_column,
                phenotype_column=phenotype_column,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Variance decomposition analysis failed.\n"
                f"- Input CSV: {prepared.phenotype_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Variance decomposition analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input CSV: {prepared.phenotype_csv_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Result CSV: {prepared.result_csv_path}",
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
        genotype_column: str | None = None,
        environment_column: str | None = None,
        phenotype_column: str | None = None,
    ) -> PreparedVarianceDecompositionRun:
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv)
        output_root = self._resolve_output_dir(output_dir)
        genotype_column_value = self._normalize_column_name(genotype_column or "LINE", "genotype_column")
        environment_column_value = self._normalize_column_name(
            environment_column or "location",
            "environment_column",
        )
        phenotype_column_value = self._normalize_column_name(phenotype_column or "PH", "phenotype_column")
        result_csv_path = output_root / "variance_components_percentage.csv"
        summary_path = output_root / "variance_components_percentage_summary.txt"

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
            "--genotype-column",
            genotype_column_value,
            "--environment-column",
            environment_column_value,
            "--phenotype-column",
            phenotype_column_value,
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedVarianceDecompositionRun(
            launcher=env_status["launcher"],
            genotype_column=genotype_column_value,
            environment_column=environment_column_value,
            phenotype_column=phenotype_column_value,
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

    def _normalize_column_name(self, value: str, field_name: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise ValueError(f"{field_name} must not be empty")
        return candidate
