"""Combining ability analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedCombiningAbilityRun:
    """Prepared execution plan for combining ability analysis."""

    launcher: str
    hybrid_column: str
    female_column: str
    male_column: str
    phenotype_column: str
    command: list[str]
    phenotype_csv_path: Path
    output_dir: Path
    female_gca_path: Path
    male_gca_path: Path
    sca_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "hybrid_column": self.hybrid_column,
            "female_column": self.female_column,
            "male_column": self.male_column,
            "phenotype_column": self.phenotype_column,
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "output_dir": str(self.output_dir),
            "female_gca_path": str(self.female_gca_path),
            "male_gca_path": str(self.male_gca_path),
            "sca_path": str(self.sca_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunCombiningAbilityTool(PlinkToolBase, Tool):
    """Estimate female GCA, male GCA, and SCA from a hybrid phenotype table."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="combining_ability_analysis",
            default_output_subdir="combining_ability",
            env_name="EasyGS_2",
        )
        self.script_path = self.skill_dir / "combining_ability.sh"
        self.r_script_path = self.skill_dir / "run_combining_ability.R"
        self.summary_script_path = self.skill_dir / "summarize_combining_ability.py"

    @property
    def name(self) -> str:
        return "run_combining_ability"

    @property
    def description(self) -> str:
        return (
            "Estimate female GCA, male GCA, and hybrid SCA from a hybrid phenotype CSV "
            "using a sommer mixed model in EasyGS_2."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Input hybrid phenotype CSV. The default expected columns are Hybrid, "
                        "Female, Male, and Phenotype. Example:\n"
                        "Hybrid,Female,Male,Phenotype\n"
                        "MG_255_X_MG_1538,MG_255,MG_1538,367.2\n"
                        "MG_255_X_MG_1531,MG_255,MG_1531,270.0\n"
                        "MG_255_X_MG_1542,MG_255,MG_1542,288.6\n"
                        "MG_283_X_MG_1538,MG_283,MG_1538,264.8"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/combining_ability/."
                    ),
                },
                "hybrid_column": {
                    "type": "string",
                    "description": "Hybrid combination column name. Defaults to 'Hybrid'.",
                },
                "female_column": {
                    "type": "string",
                    "description": "Female parent column name. Defaults to 'Female'.",
                },
                "male_column": {
                    "type": "string",
                    "description": "Male parent column name. Defaults to 'Male'.",
                },
                "phenotype_column": {
                    "type": "string",
                    "description": "Phenotype value column name. Defaults to 'Phenotype'.",
                },
            },
            "required": ["phenotype_csv"],
        }

    async def execute(
        self,
        phenotype_csv: str,
        output_dir: str | None = None,
        hybrid_column: str | None = None,
        female_column: str | None = None,
        male_column: str | None = None,
        phenotype_column: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                phenotype_csv=phenotype_csv,
                output_dir=output_dir,
                hybrid_column=hybrid_column,
                female_column=female_column,
                male_column=male_column,
                phenotype_column=phenotype_column,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Combining ability analysis failed.\n"
                f"- Input CSV: {prepared.phenotype_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Combining ability analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input CSV: {prepared.phenotype_csv_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Female GCA CSV: {prepared.female_gca_path}",
            f"- Male GCA CSV: {prepared.male_gca_path}",
            f"- SCA CSV: {prepared.sca_path}",
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
        hybrid_column: str | None = None,
        female_column: str | None = None,
        male_column: str | None = None,
        phenotype_column: str | None = None,
    ) -> PreparedCombiningAbilityRun:
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv)
        output_root = self._resolve_output_dir(output_dir)
        hybrid_column_value = self._normalize_column_name(hybrid_column or "Hybrid", "hybrid_column")
        female_column_value = self._normalize_column_name(female_column or "Female", "female_column")
        male_column_value = self._normalize_column_name(male_column or "Male", "male_column")
        phenotype_column_value = self._normalize_column_name(phenotype_column or "Phenotype", "phenotype_column")

        female_gca_path = output_root / "Female_gca.csv"
        male_gca_path = output_root / "Male_gca.csv"
        sca_path = output_root / "sca.csv"
        summary_path = output_root / "combining_ability_summary.txt"

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
            "--female-gca-output",
            str(female_gca_path),
            "--male-gca-output",
            str(male_gca_path),
            "--sca-output",
            str(sca_path),
            "--summary-output",
            str(summary_path),
            "--hybrid-column",
            hybrid_column_value,
            "--female-column",
            female_column_value,
            "--male-column",
            male_column_value,
            "--phenotype-column",
            phenotype_column_value,
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedCombiningAbilityRun(
            launcher=env_status["launcher"],
            hybrid_column=hybrid_column_value,
            female_column=female_column_value,
            male_column=male_column_value,
            phenotype_column=phenotype_column_value,
            command=command,
            phenotype_csv_path=phenotype_csv_path,
            output_dir=output_root,
            female_gca_path=female_gca_path,
            male_gca_path=male_gca_path,
            sca_path=sca_path,
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
