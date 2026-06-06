"""Cross-region phenotype correlation and heatmap analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedPhenotypeRegionCorrelationRun:
    """Prepared cross-region phenotype correlation execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    phe_csv_path: Path
    output_dir: Path
    correlation_csv_path: Path
    heatmap_pdf_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "phe_csv_path": str(self.phe_csv_path),
            "output_dir": str(self.output_dir),
            "correlation_csv_path": str(self.correlation_csv_path),
            "heatmap_pdf_path": str(self.heatmap_pdf_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunPhenotypeRegionCorrelationTool(PlinkToolBase, Tool):
    """Compute phenotype correlations across region columns and render a heatmap PDF."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="phenotype_region_correlation_analysis",
            default_output_subdir="phenotype_region_correlation",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "phenotype_region_correlation.sh"
        self.r_script_path = self.skill_dir / "phenotype_region_correlation_heatmap.R"
        self.summary_script_path = self.skill_dir / "summarize_phenotype_region_correlation.py"

    @property
    def name(self) -> str:
        return "run_phenotype_region_correlation"

    @property
    def description(self) -> str:
        return (
            "Compute the correlation matrix between region-level phenotype columns from a "
            "phe.csv-style file and render a heatmap PDF."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phe_csv": {
                    "type": "string",
                    "description": (
                        "Input phe.csv-style file. Expected format starts with one sample ID column "
                        "followed by phenotype columns for each region. Example:\n"
                        "ID,PH_JL,PH_LN,PH_BJ,PH_HB,PH_HN\n"
                        "MG_49,234.6,241.13,249.6,228.8,215.25\n"
                        "MG_50,217.2,204,212.2,196.75,173.6\n"
                        "MG_51,198.5,207.4,202.75,233.33,166.2\n"
                        "MG_52,209.8,230.5,209.8,189.4,184.5\n"
                        "MG_53,219.2,200,224.25,183.75,182.25"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/phenotype_region_correlation/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for outputs. Defaults to '各地区表型相关性', producing "
                        "<prefix>.csv and <prefix>.pdf."
                    ),
                },
            },
            "required": ["phe_csv"],
        }

    async def execute(
        self,
        phe_csv: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                phe_csv=phe_csv,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Cross-region phenotype correlation analysis failed.\n"
                f"- Input CSV: {prepared.phe_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Cross-region phenotype correlation analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input CSV: {prepared.phe_csv_path}",
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
        phe_csv: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedPhenotypeRegionCorrelationRun:
        phe_csv_path = self._resolve_phe_csv(phe_csv)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "各地区表型相关性")
        correlation_csv_path = output_root / f"{prefix_name}.csv"
        heatmap_pdf_path = output_root / f"{prefix_name}.pdf"
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
            str(phe_csv_path),
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

        return PreparedPhenotypeRegionCorrelationRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            phe_csv_path=phe_csv_path,
            output_dir=output_root,
            correlation_csv_path=correlation_csv_path,
            heatmap_pdf_path=heatmap_pdf_path,
            summary_path=summary_path,
        )

    def _resolve_phe_csv(self, phe_csv: str) -> Path:
        phe_csv_path = _resolve_path(phe_csv, self.allowed_dir)
        if not phe_csv_path.exists():
            raise ValueError(f"Input CSV not found: {phe_csv_path}")
        if not phe_csv_path.is_file():
            raise ValueError(f"Input phe.csv must be a file: {phe_csv_path}")
        if phe_csv_path.suffix.lower() != ".csv":
            raise ValueError(f"Input phenotype file must end with .csv: {phe_csv_path}")
        return phe_csv_path
