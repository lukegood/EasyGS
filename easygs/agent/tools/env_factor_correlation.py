"""Environmental-factor correlation and heatmap analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedEnvFactorCorrelationRun:
    """Prepared environmental-factor correlation execution plan."""

    launcher: str
    prefix: str
    region: str
    command: list[str]
    env_csv_path: Path
    output_dir: Path
    correlation_csv_path: Path
    heatmap_pdf_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "region": self.region,
            "env_csv_path": str(self.env_csv_path),
            "output_dir": str(self.output_dir),
            "correlation_csv_path": str(self.correlation_csv_path),
            "heatmap_pdf_path": str(self.heatmap_pdf_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunEnvFactorCorrelationTool(PlinkToolBase, Tool):
    """Compute EF correlations for one region and render a heatmap PDF."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="env_factor_correlation_analysis",
            default_output_subdir="env_factor_correlation",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "env_factor_correlation.sh"
        self.r_script_path = self.skill_dir / "env_factor_correlation_heatmap.R"
        self.summary_script_path = self.skill_dir / "summarize_env_factor_correlation.py"

    @property
    def name(self) -> str:
        return "run_env_factor_correlation"

    @property
    def description(self) -> str:
        return (
            "Compute the correlation matrix for environmental factors in a specified region "
            "from an env.csv-style file and render a heatmap PDF."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "env_csv": {
                    "type": "string",
                    "description": (
                        "Input env.csv-style file. Expected format starts with region and date "
                        "columns followed by environmental factor columns. Example:\n"
                        "env_code\tDate\tDL\tGDD\tdGDD\n"
                        "Beijing\t2014/5/13\t14.311\t22.347\t0\n"
                        "Beijing\t2014/5/14\t14.344\t14.328\t8.019\n"
                        "Beijing\t2014/5/15\t14.376\t19.071\t4.743\n"
                        "Beijing\t2014/5/16\t14.407\t20.691\t1.62\n"
                        "Beijing\t2014/5/17\t14.439\t17.109\t3.582\n"
                        "Beijing\t2014/5/18\t14.469\t22.131\t5.022\n"
                        "Beijing\t2014/5/19\t14.499\t25.371\t3.24\n"
                        "Beijing\t2014/5/20\t14.528\t25.083\t0.288\n"
                        "Beijing\t2014/5/21\t14.557\t23.085\t1.998\n"
                        "Beijing\t2014/5/22\t14.585\t27.306\t4.221"
                    ),
                },
                "region": {
                    "type": "string",
                    "description": "Region name to subset, such as 'Beijing'.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/env_factor_correlation/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for outputs. Defaults to '<region>_25EF_cor', producing "
                        "<prefix>.csv and <prefix>_heatmap.pdf."
                    ),
                },
            },
            "required": ["env_csv", "region"],
        }

    async def execute(
        self,
        env_csv: str,
        region: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                env_csv=env_csv,
                region=region,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Environmental-factor correlation analysis failed.\n"
                f"- Input CSV: {prepared.env_csv_path}\n"
                f"- Region: {prepared.region}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Environmental-factor correlation analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input CSV: {prepared.env_csv_path}",
            f"- Region: {prepared.region}",
            f"- Output dir: {prepared.output_dir}",
            f"- Correlation CSV: {prepared.correlation_csv_path}",
            f"- Heatmap PDF: {prepared.heatmap_pdf_path}",
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
        env_csv: str,
        region: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedEnvFactorCorrelationRun:
        env_csv_path = self._resolve_env_csv(env_csv)
        region_name = (region or "").strip()
        if not region_name:
            raise ValueError("region must be a non-empty string")

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, f"{region_name}_25EF_cor")
        correlation_csv_path = output_root / f"{prefix_name}.csv"
        heatmap_pdf_path = output_root / f"{prefix_name}_heatmap.pdf"
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
            str(env_csv_path),
            "--region",
            region_name,
            "--cor-output",
            str(correlation_csv_path),
            "--pdf-output",
            str(heatmap_pdf_path),
            "--summary-output",
            str(summary_path),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedEnvFactorCorrelationRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            region=region_name,
            command=command,
            env_csv_path=env_csv_path,
            output_dir=output_root,
            correlation_csv_path=correlation_csv_path,
            heatmap_pdf_path=heatmap_pdf_path,
            summary_path=summary_path,
        )

    def _resolve_env_csv(self, env_csv: str) -> Path:
        env_csv_path = _resolve_path(env_csv, self.allowed_dir)
        if not env_csv_path.exists():
            raise ValueError(f"Input CSV not found: {env_csv_path}")
        if not env_csv_path.is_file():
            raise ValueError(f"Input CSV must be a file: {env_csv_path}")
        if env_csv_path.suffix.lower() != ".csv":
            raise ValueError(f"Input file must be a .csv file: {env_csv_path}")
        return env_csv_path
