"""Environment index analysis tool based on the CERIS workflow."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedEnvironmentIndexRun:
    """Prepared environment-index execution plan."""

    launcher: str
    trait_label: str
    trait_column: str
    command: list[str]
    env_meta_path: Path
    trait_records_path: Path
    env_paras_path: Path
    run_downstream: bool
    output_dir: Path
    trait_dir_path: Path
    allwinds_path: Path
    highest_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "trait_label": self.trait_label,
            "trait_column": self.trait_column,
            "env_meta_path": str(self.env_meta_path),
            "trait_records_path": str(self.trait_records_path),
            "env_paras_path": str(self.env_paras_path),
            "run_downstream": self.run_downstream,
            "output_dir": str(self.output_dir),
            "trait_dir_path": str(self.trait_dir_path),
            "allwinds_path": str(self.allwinds_path),
            "highest_path": str(self.highest_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunEnvironmentIndexTool(PlinkToolBase, Tool):
    """Run the CERIS-style environment index workflow on EnvPheno inputs."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="environment_index_analysis",
            default_output_subdir="environment_index",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "environment_index.sh"
        self.r_script_path = self.skill_dir / "run_environment_index.R"
        self.subfunctions_path = self.skill_dir / "Sub_functions.r"
        self.summary_script_path = self.skill_dir / "summarize_environment_index.py"

    @property
    def name(self) -> str:
        return "run_environment_index"

    @property
    def description(self) -> str:
        return (
            "Run the CERIS-style environment index workflow from environment metadata, "
            "trait records, and environment-parameter tables, then generate allwinds/highest "
            "summaries with optional selected-window downstream outputs."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "env_meta": {
                    "type": "string",
                    "description": (
                        "Path to Env_meta_table.txt. This is typically a UTF-16LE tab-delimited file "
                        "with environment code, latitude, longitude, planting date, trial year, and "
                        "environment note. Example:\n"
                        "env_code\tlat\tlon\tPlantingDate\tTrialYear\tenv_note\n"
                        "Jilin\t43.88\t125.35\t2014-05-09\t2014\t14JL\n"
                        "Liaoning\t41.48\t123.38\t2014-05-11\t2014\t14LN\n"
                        "Beijing\t40.13\t116.13\t2014-05-13\t2014\t14BJ\n"
                        "Hebei\t38.85\t115.48\t2014-06-11\t2014\t14HB\n"
                        "Henan\t35.31\t113.85\t2014-06-12\t2014\t14HN"
                    ),
                },
                "trait_records": {
                    "type": "string",
                    "description": (
                        "Path to Trait_records.txt. This should be a tab-delimited table containing "
                        "line_code, env_code, and the trait column to analyze. Example:\n"
                        "line_code\tenv_code\tPH\n"
                        "MG_49\tJilin\t234.6\n"
                        "MG_50\tJilin\t217.2\n"
                        "MG_51\tJilin\t198.5\n"
                        "MG_52\tJilin\t209.8"
                    ),
                },
                "env_paras": {
                    "type": "string",
                    "description": (
                        "Path to 5Envs_envParas_DAP150.txt or a compatible tab-delimited file. "
                        "Dates must use strict YYYY-MM-DD format. Example:\n"
                        "env_code\tDate\tDL\tGDD\tdGDD\tDTR\tPTT\tPTR\tPTD1\tPTD2\tTSR\tMMR\tPR\tRH\tPRDTR\tdPTT\tPS\tWS\tWD\tAPAR\tCPAR\tUVA\tUVB\tSW\tSM\tTMAX\tTMIN\n"
                        "Jilin\t2014-05-09\t14.554\t10.548\t0\t35.856\t153.5156\t0.7247\t521.8482\t2.4637\t3812.7836\t0.4957\t0\t54.25\t0\t0\t99.67\t1.82\t282.5\t138.04\t143.95\t18.14\t0.28\t0.56\t0.58\t71.096\t35.24\n"
                        "Jilin\t2014-05-10\t14.596\t9.405\t1.143\t22.716\t137.2754\t0.6444\t331.5627\t1.5563\t2610.1593\t0.6699\t0.01\t64.12\t4.00E-04\t16.2402\t99.81\t1.77\t211.25\t68.24\t103.94\t8.38\t0.15\t0.56\t0.58\t68.81\t46.094\n"
                        "Jilin\t2014-05-11\t14.637\t7.929\t1.476\t15.678\t116.0568\t0.5417\t229.4789\t1.0711\t1816.4217\t0.7616\t7.29\t78.81\t0.465\t21.2186\t99.03\t2.23\t169.31\t47.31\t121.52\t6.59\t0.13\t0.56\t0.58\t65.768\t50.09"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/environment_index/."
                    ),
                },
                "trait_label": {
                    "type": "string",
                    "description": (
                        "Name used for the trait-specific output directory and filenames. "
                        "Defaults to 'testPH'."
                    ),
                },
                "trait_column": {
                    "type": "string",
                    "description": (
                        "Column name in Trait_records.txt to analyze. Defaults to 'PH'."
                    ),
                },
                "searching_daps": {
                    "type": "integer",
                    "description": "Number of DAP rows searched for windows. Defaults to 150.",
                },
                "max_window_start": {
                    "type": "integer",
                    "description": "Selected best-window start day for downstream plots when run_downstream=true. Defaults to 13.",
                },
                "max_window_end": {
                    "type": "integer",
                    "description": "Selected best-window end day for downstream plots when run_downstream=true. Defaults to 40.",
                },
                "key_parameter": {
                    "type": "string",
                    "description": "Environmental parameter used for downstream plots and LOO output when run_downstream=true. Defaults to 'PTT'.",
                },
                "run_downstream": {
                    "type": "boolean",
                    "description": (
                        "Whether to run the downstream selected-window plots, slope/intercept table, "
                        "and LOOCV after allwinds_EF_cor.csv and highest_EF.csv. Defaults to false "
                        "to match the active portion of run_CERIS.R."
                    ),
                },
                "env_meta_encoding": {
                    "type": "string",
                    "description": "Encoding used to read Env_meta_table.txt. Defaults to 'UTF-16LE'.",
                },
            },
            "required": ["env_meta", "trait_records", "env_paras"],
        }

    async def execute(
        self,
        env_meta: str,
        trait_records: str,
        env_paras: str,
        output_dir: str | None = None,
        trait_label: str | None = None,
        trait_column: str | None = None,
        searching_daps: int | None = None,
        max_window_start: int | None = None,
        max_window_end: int | None = None,
        key_parameter: str | None = None,
        run_downstream: bool | None = None,
        env_meta_encoding: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                env_meta=env_meta,
                trait_records=trait_records,
                env_paras=env_paras,
                output_dir=output_dir,
                trait_label=trait_label,
                trait_column=trait_column,
                searching_daps=searching_daps,
                max_window_start=max_window_start,
                max_window_end=max_window_end,
                key_parameter=key_parameter,
                run_downstream=run_downstream,
                env_meta_encoding=env_meta_encoding,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Environment index analysis failed.\n"
                f"- Env meta: {prepared.env_meta_path}\n"
                f"- Trait records: {prepared.trait_records_path}\n"
                f"- Env paras: {prepared.env_paras_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Environment index analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Env meta: {prepared.env_meta_path}",
            f"- Trait records: {prepared.trait_records_path}",
            f"- Env paras: {prepared.env_paras_path}",
            f"- Run downstream: {prepared.run_downstream}",
            f"- Output dir: {prepared.output_dir}",
            f"- Trait output dir: {prepared.trait_dir_path}",
            f"- allwinds_EF_cor.csv: {prepared.allwinds_path}",
            f"- highest_EF.csv: {prepared.highest_path}",
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
        env_meta: str,
        trait_records: str,
        env_paras: str,
        output_dir: str | None = None,
        trait_label: str | None = None,
        trait_column: str | None = None,
        searching_daps: int | None = None,
        max_window_start: int | None = None,
        max_window_end: int | None = None,
        key_parameter: str | None = None,
        run_downstream: bool | None = None,
        env_meta_encoding: str | None = None,
    ) -> PreparedEnvironmentIndexRun:
        env_meta_path = self._resolve_text_file(env_meta, "Env meta")
        trait_records_path = self._resolve_text_file(trait_records, "Trait records")
        env_paras_path = self._resolve_text_file(env_paras, "Environment-parameter")
        output_root = self._resolve_output_dir(output_dir)

        trait_label_value = self._normalize_name(trait_label, "testPH", "trait_label")
        trait_column_value = self._normalize_name(trait_column, "PH", "trait_column")
        key_parameter_value = self._normalize_name(key_parameter, "PTT", "key_parameter")
        run_downstream_value = self._normalize_bool(run_downstream, False, "run_downstream")
        env_meta_encoding_value = self._normalize_name(env_meta_encoding, "UTF-16LE", "env_meta_encoding")

        searching_daps_value = 150 if searching_daps is None else int(searching_daps)
        max_window_start_value = 13 if max_window_start is None else int(max_window_start)
        max_window_end_value = 40 if max_window_end is None else int(max_window_end)
        if searching_daps_value < 7:
            raise ValueError("searching_daps must be at least 7")
        if max_window_start_value < 1:
            raise ValueError("max_window_start must be at least 1")
        if max_window_end_value < max_window_start_value:
            raise ValueError("max_window_end must be greater than or equal to max_window_start")

        trait_dir_path = output_root / trait_label_value
        allwinds_path = output_root / "allwinds_EF_cor.csv"
        highest_path = output_root / "highest_EF.csv"
        summary_path = output_root / "environment_index_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "R script": self.r_script_path,
            "subfunction script": self.subfunctions_path,
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
            "--env-meta",
            str(env_meta_path),
            "--trait-records",
            str(trait_records_path),
            "--env-paras",
            str(env_paras_path),
            "--output-dir",
            str(output_root),
            "--trait-label",
            trait_label_value,
            "--trait-column",
            trait_column_value,
            "--searching-daps",
            str(searching_daps_value),
            "--max-window-start",
            str(max_window_start_value),
            "--max-window-end",
            str(max_window_end_value),
            "--key-parameter",
            key_parameter_value,
            "--run-downstream",
            "1" if run_downstream_value else "0",
            "--env-meta-encoding",
            env_meta_encoding_value,
            "--r-script",
            str(self.r_script_path),
            "--subfunctions-script",
            str(self.subfunctions_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedEnvironmentIndexRun(
            launcher=env_status["launcher"],
            trait_label=trait_label_value,
            trait_column=trait_column_value,
            command=command,
            env_meta_path=env_meta_path,
            trait_records_path=trait_records_path,
            env_paras_path=env_paras_path,
            run_downstream=run_downstream_value,
            output_dir=output_root,
            trait_dir_path=trait_dir_path,
            allwinds_path=allwinds_path,
            highest_path=highest_path,
            summary_path=summary_path,
        )

    def _resolve_text_file(self, value: str, label: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"{label} file not found: {path}")
        if not path.is_file():
            raise ValueError(f"{label} input must be a file: {path}")
        return path

    def _normalize_name(self, value: str | None, default: str, field_name: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            candidate = default
        if "/" in candidate or "\\" in candidate:
            raise ValueError(f"{field_name} must not contain path separators: {candidate}")
        return candidate

    def _normalize_bool(self, value: bool | str | int | None, default: bool, field_name: str) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            raise ValueError(f"{field_name} must be a boolean")
        candidate = str(value).strip().lower()
        if candidate in {"1", "true", "yes", "y"}:
            return True
        if candidate in {"0", "false", "no", "n"}:
            return False
        raise ValueError(f"{field_name} must be a boolean")
