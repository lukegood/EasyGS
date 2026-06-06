"""rrBLUP genomic prediction tool with explicit user-provided CSV inputs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedRrblupPredictionRun:
    """Prepared execution plan for rrBLUP genomic prediction."""

    launcher: str
    id_column: str
    cv_column: str
    trait_name: str
    expected_folds: int
    command: list[str]
    genotype_csv_paths: list[Path]
    phenotype_csv_paths: list[Path]
    cv_csv_paths: list[Path]
    output_dir: Path
    output_prefix: str
    fold_metrics_path: Path
    mean_effect_path: Path
    mean_intercept_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "id_column": self.id_column,
            "cv_column": self.cv_column,
            "trait_name": self.trait_name,
            "expected_folds": self.expected_folds,
            "genotype_csv_paths": [str(path) for path in self.genotype_csv_paths],
            "phenotype_csv_paths": [str(path) for path in self.phenotype_csv_paths],
            "cv_csv_paths": [str(path) for path in self.cv_csv_paths],
            "output_dir": str(self.output_dir),
            "output_prefix": self.output_prefix,
            "fold_metrics_path": str(self.fold_metrics_path),
            "mean_effect_path": str(self.mean_effect_path),
            "mean_intercept_path": str(self.mean_intercept_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunRrblupPredictionTool(PlinkToolBase, Tool):
    """Run rrBLUP-based genomic prediction from explicit genotype/phenotype/CV CSV files."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="rrblup_prediction_analysis",
            default_output_subdir="rrblup_prediction",
            env_name="EasyGS_3",
        )
        self.script_path = self.skill_dir / "rrblup_prediction.sh"
        self.r_script_path = self.skill_dir / "run_rrblup_prediction.R"
        self.summary_script_path = self.skill_dir / "summarize_rrblup_prediction.py"

    @property
    def name(self) -> str:
        return "run_rrblup_prediction"

    @property
    def description(self) -> str:
        return (
            "Run rrBLUP genomic prediction in EasyGS_3 from explicit user-provided genotype CSVs, "
            "phenotype CSVs, and CV CSVs, then export fold predictions and mean marker effects."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "genotype_csvs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One or more user-provided genotype CSV files. Each file must have sample IDs "
                        "in the first column and numeric marker columns after that. Example rows:\n"
                        "ID,ZMPV01aSNPC01P000049527,ZMPV01aSNPC01P000172921,ZMPV01aSNPC01P000277229,ZMPV01aSNPC01P000277887\n"
                        "04K5672,0,0,0,0\n"
                        "04K5686,0,0,0,0\n"
                        "04K5702,2,2,0,0\n"
                        "05W002,2,0,2,2"
                    ),
                },
                "phenotype_csvs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One or more user-provided phenotype CSV files. The first column must be sample IDs, "
                        "and the trait column named by trait_name must exist. Example rows:\n"
                        "ID,Plantheight,Earheight,Earleafwidth,Earleaflength\n"
                        "04K5672,-1.3060108678835813,-0.33363640998930855,-1.9886244144669243,-0.4752590274927541\n"
                        "04K5686,-0.9900750166857649,-1.337881288370562,-2.2065216365462392,-1.010483071516264\n"
                        "04K5702,-0.6050885223173679,-0.8208113705636478,-1.3213004287428514,-0.03339737340988433\n"
                        "05W002,-0.11894641928673357,-0.004839335792526001,0.15557827597605214,-0.3097918084832566"
                    ),
                },
                "cv_csvs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "One or more user-provided cross-validation assignment CSV files. Example rows:\n"
                        "ID,cv_1\n"
                        "04K5672,1\n"
                        "04K5686,9\n"
                        "04K5702,1\n"
                        "05W002,4"
                    ),
                },
                "trait_name": {
                    "type": "string",
                    "description": (
                        "Trait column name to predict from the phenotype CSV files, for example "
                        "`X100grainweight`. This parameter is required."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Default: workspace/default_results/rrblup_prediction/. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional output filename prefix. Default: rrBLUP_<trait_name>. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "id_column": {
                    "type": "string",
                    "description": (
                        "Sample-ID column name expected in phenotype and CV CSVs, and the first column "
                        "name in genotype CSVs. Default: ID. If you want to override it, please provide it explicitly."
                    ),
                },
                "cv_column": {
                    "type": "string",
                    "description": (
                        "Cross-validation fold column name in cv_csvs. Default: cv_1. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "expected_folds": {
                    "type": "integer",
                    "minimum": 2,
                    "description": (
                        "Expected number of CV folds. Default: 10. If you want to override it, "
                        "please provide it explicitly."
                    ),
                },
            },
            "required": ["genotype_csvs", "phenotype_csvs", "cv_csvs", "trait_name"],
        }

    async def execute(
        self,
        genotype_csvs: list[str],
        phenotype_csvs: list[str],
        cv_csvs: list[str],
        trait_name: str,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        id_column: str | None = None,
        cv_column: str | None = None,
        expected_folds: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                genotype_csvs=genotype_csvs,
                phenotype_csvs=phenotype_csvs,
                cv_csvs=cv_csvs,
                trait_name=trait_name,
                output_dir=output_dir,
                output_prefix=output_prefix,
                id_column=id_column,
                cv_column=cv_column,
                expected_folds=expected_folds,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: rrBLUP genomic prediction failed.\n"
                f"- Trait: {prepared.trait_name}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "rrBLUP genomic prediction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Trait: {prepared.trait_name}",
            f"- Genotype CSVs: {', '.join(str(path) for path in prepared.genotype_csv_paths)}",
            f"- Phenotype CSVs: {', '.join(str(path) for path in prepared.phenotype_csv_paths)}",
            f"- CV CSVs: {', '.join(str(path) for path in prepared.cv_csv_paths)}",
            f"- ID column: {prepared.id_column}",
            f"- CV column: {prepared.cv_column}",
            f"- Expected folds: {prepared.expected_folds}",
            f"- Output dir: {prepared.output_dir}",
            f"- Fold metrics CSV: {prepared.fold_metrics_path}",
            f"- Mean effect CSV: {prepared.mean_effect_path}",
            f"- Mean intercept CSV: {prepared.mean_intercept_path}",
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
        genotype_csvs: list[str],
        phenotype_csvs: list[str],
        cv_csvs: list[str],
        trait_name: str,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        id_column: str | None = None,
        cv_column: str | None = None,
        expected_folds: int | None = None,
    ) -> PreparedRrblupPredictionRun:
        genotype_paths = self._resolve_file_list(genotype_csvs, "Genotype CSVs")
        phenotype_paths = self._resolve_file_list(phenotype_csvs, "Phenotype CSVs")
        cv_paths = self._resolve_file_list(cv_csvs, "CV CSVs")

        trait_value = (trait_name or "").strip()
        if not trait_value:
            raise ValueError("trait_name is required.")

        id_column_value = (id_column or "ID").strip() or "ID"
        cv_column_value = (cv_column or "cv_1").strip() or "cv_1"
        expected_folds_value = expected_folds or 10
        if expected_folds_value < 2:
            raise ValueError("expected_folds must be at least 2.")

        for path in genotype_paths:
            self._validate_genotype_csv(path, id_column_value)
        for path in phenotype_paths:
            self._validate_csv_header(path, id_column_value, f"Phenotype CSV ({path.name})")
            self._validate_csv_header(path, trait_value, f"Phenotype CSV ({path.name})")
        for path in cv_paths:
            self._validate_csv_header(path, id_column_value, f"CV CSV ({path.name})")
            self._validate_csv_header(path, cv_column_value, f"CV CSV ({path.name})")

        output_root = self._resolve_output_dir(output_dir)
        output_prefix_value = self._normalize_prefix_name(
            output_prefix,
            f"rrBLUP_{trait_value}",
        )
        fold_metrics_path = output_root / f"{output_prefix_value}_fold_metrics.csv"
        mean_effect_path = output_root / f"{output_prefix_value}_mean_effect.csv"
        mean_intercept_path = output_root / f"{output_prefix_value}_mean_intercept.csv"
        summary_path = output_root / f"{output_prefix_value}_summary.txt"

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
            "--genotype-csvs",
            ",".join(str(path) for path in genotype_paths),
            "--phenotype-csvs",
            ",".join(str(path) for path in phenotype_paths),
            "--cv-csvs",
            ",".join(str(path) for path in cv_paths),
            "--trait-name",
            trait_value,
            "--id-column",
            id_column_value,
            "--cv-column",
            cv_column_value,
            "--expected-folds",
            str(expected_folds_value),
            "--output-dir",
            str(output_root),
            "--output-prefix",
            output_prefix_value,
            "--fold-metrics-output",
            str(fold_metrics_path),
            "--mean-effect-output",
            str(mean_effect_path),
            "--mean-intercept-output",
            str(mean_intercept_path),
            "--summary-output",
            str(summary_path),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedRrblupPredictionRun(
            launcher=env_status["launcher"],
            id_column=id_column_value,
            cv_column=cv_column_value,
            trait_name=trait_value,
            expected_folds=expected_folds_value,
            command=command,
            genotype_csv_paths=genotype_paths,
            phenotype_csv_paths=phenotype_paths,
            cv_csv_paths=cv_paths,
            output_dir=output_root,
            output_prefix=output_prefix_value,
            fold_metrics_path=fold_metrics_path,
            mean_effect_path=mean_effect_path,
            mean_intercept_path=mean_intercept_path,
            summary_path=summary_path,
        )

    def _resolve_file_list(self, values: list[str] | None, label: str) -> list[Path]:
        if not values:
            raise ValueError(f"{label} are required.")
        resolved: list[Path] = []
        for raw in values:
            candidate = (raw or "").strip()
            if not candidate:
                continue
            path = _resolve_path(candidate, self.allowed_dir)
            if not path.exists():
                raise ValueError(f"{label} file not found: {path}")
            if not path.is_file():
                raise ValueError(f"{label} entry must be a file: {path}")
            resolved.append(path)
        if not resolved:
            raise ValueError(f"{label} are required.")
        return resolved

    def _validate_csv_header(self, path: Path, expected_column: str, label: str) -> None:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"{label} is empty: {path}") from exc
        if expected_column not in header:
            raise ValueError(f"{label} must contain column '{expected_column}': {path}")

    def _validate_genotype_csv(self, path: Path, id_column: str) -> None:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"Genotype CSV is empty: {path}") from exc

            if len(header) < 3:
                raise ValueError(f"Genotype CSV must contain ID plus at least two marker columns: {path}")
            if header[0] != id_column:
                raise ValueError(
                    f"Genotype CSV first column must be '{id_column}' to match the configured ID column: {path}"
                )

            checked_rows = 0
            for row in reader:
                if not row:
                    continue
                if len(row) < 3:
                    raise ValueError(f"Genotype CSV row has too few columns: {path}")
                checked_rows += 1
                if checked_rows >= 3:
                    break
            if checked_rows == 0:
                raise ValueError(f"Genotype CSV has no data rows: {path}")
