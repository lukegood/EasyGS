"""VCF to genomic-prediction genotype CSV conversion tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedVcfGenomicPredictionCsvRun:
    """Prepared VCF-to-genomic-prediction-CSV execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    output_dir: Path
    output_csv_path: Path
    marker_csv_path: Path
    summary_path: Path
    transpose: bool
    keep_marker_csv: bool
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "output_dir": str(self.output_dir),
            "output_csv_path": str(self.output_csv_path),
            "csv_path": str(self.output_csv_path),
            "marker_csv_path": str(self.marker_csv_path),
            "summary_path": str(self.summary_path),
            "transpose": self.transpose,
            "keep_marker_csv": self.keep_marker_csv,
            "notes": list(self.notes),
        }



class RunVcfGenomicPredictionCsvTool(PlinkToolBase, Tool):
    """Prepare a 0/1/2 genotype CSV matrix for genomic prediction algorithms."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="vcf_genomic_prediction_csv_analysis",
            default_output_subdir="vcf_genomic_prediction_csv",
        )
        self.script_path = self.skill_dir / "vcf_genomic_prediction_csv.py"

    @property
    def name(self) -> str:
        return "run_vcf_genomic_prediction_csv"

    @property
    def description(self) -> str:
        return (
            "Convert a VCF/VCF.GZ file into a 0/1/2 additive genotype CSV matrix prepared for "
            "genomic prediction methods using the EasyGS_2 environment. Defaults to a "
            "sample-by-marker matrix with samples as rows and variant IDs as columns."
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
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/vcf_genomic_prediction_csv/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for outputs. Defaults to 'genomic_prediction_genotype'. Generates "
                        "<prefix>_final_transposed.csv by default."
                    ),
                },
                "transpose": {
                    "type": "boolean",
                    "description": (
                        "Whether to transpose the marker-by-sample intermediate matrix into the "
                        "sample-by-marker layout expected by most genomic prediction workflows. "
                        "Defaults to true."
                    ),
                },
                "keep_marker_csv": {
                    "type": "boolean",
                    "description": (
                        "Whether to keep the intermediate marker x sample CSV when transposing. "
                        "Defaults to false."
                    ),
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        transpose: bool | None = None,
        keep_marker_csv: bool | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                output_dir=output_dir,
                prefix=prefix,
                transpose=transpose,
                keep_marker_csv=keep_marker_csv,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: VCF to genomic-prediction CSV conversion failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Output CSV: {prepared.output_csv_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "VCF to genomic-prediction CSV conversion completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Output CSV: {prepared.output_csv_path}",
            f"- Marker CSV: {prepared.marker_csv_path if prepared.keep_marker_csv else 'not kept'}",
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
        output_dir: str | None = None,
        prefix: str | None = None,
        transpose: bool | None = None,
        keep_marker_csv: bool | None = None,
    ) -> PreparedVcfGenomicPredictionCsvRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "genomic_prediction_genotype")
        resolved_transpose = True if transpose is None else transpose
        resolved_keep_marker_csv = False if keep_marker_csv is None else keep_marker_csv

        output_suffix = "_final_transposed.csv" if resolved_transpose else "_final.csv"
        output_csv_path = output_root / f"{prefix_name}{output_suffix}"
        marker_csv_path = output_root / f"{prefix_name}_marker_matrix.csv"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        if not self.script_path.exists():
            raise ValueError(f"pipeline script not found: {self.script_path}")

        env_status = await self._get_environment_status(["python3"])
        if env_status["error"]:
            error = env_status["error"]
            raise ValueError(error[7:] if error.startswith("Error: ") else error)

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "python3",
            str(self.script_path),
            "--vcf",
            str(vcf_path),
            "--output",
            str(output_csv_path),
            "--marker-csv",
            str(marker_csv_path),
            "--summary-output",
            str(summary_path),
            "--transpose",
            "1" if resolved_transpose else "0",
            "--keep-marker-csv",
            "1" if resolved_keep_marker_csv else "0",
        ]

        return PreparedVcfGenomicPredictionCsvRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            output_dir=output_root,
            output_csv_path=output_csv_path,
            marker_csv_path=marker_csv_path,
            summary_path=summary_path,
            transpose=resolved_transpose,
            keep_marker_csv=resolved_keep_marker_csv,
        )
