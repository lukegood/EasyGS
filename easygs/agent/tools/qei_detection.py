"""QEI detection tool backed by Fast3VmrMLM."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedQeiDetectionRun:
    """Prepared execution plan for QEI detection."""

    launcher: str
    phenotype_id_column: str
    structure_id_column: str
    trait_count: int
    n_en: list[int]
    geno_type: str
    svrad: float
    svpal: float
    svmlod: float
    n_threads: int
    draw_plot: bool
    plot_format: str
    command: list[str]
    bfile_prefix_path: Path
    phenotype_csv_path: Path
    structure_csv_path: Path
    output_dir: Path
    output_prefix_path: Path
    prekinship_path: Path
    midresult_paths: list[Path]
    result_xlsx_paths: list[Path]
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "phenotype_id_column": self.phenotype_id_column,
            "structure_id_column": self.structure_id_column,
            "trait_count": self.trait_count,
            "n_en": list(self.n_en),
            "geno_type": self.geno_type,
            "svrad": self.svrad,
            "svpal": self.svpal,
            "svmlod": self.svmlod,
            "n_threads": self.n_threads,
            "draw_plot": self.draw_plot,
            "plot_format": self.plot_format,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "structure_csv_path": str(self.structure_csv_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "prekinship_path": str(self.prekinship_path),
            "midresult_paths": [str(path) for path in self.midresult_paths],
            "result_xlsx_paths": [str(path) for path in self.result_xlsx_paths],
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunQeiDetectionTool(PlinkToolBase, Tool):
    """Run Fast3VmrMLM multi-environment QEI detection from BFILE, phenotype CSV, and Q CSV."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="qei_detection_analysis",
            default_output_subdir="qei_detection",
            env_name="EasyGS_4",
        )
        self.script_path = self.skill_dir / "qei_detection.sh"
        self.r_script_path = self.skill_dir / "run_qei_detection.R"
        self.summary_script_path = self.skill_dir / "summarize_qei_detection.py"

    @property
    def name(self) -> str:
        return "run_qei_detection"

    @property
    def description(self) -> str:
        return (
            "Run Fast3VmrMLM multi-environment QEI detection in EasyGS_4 from a PLINK BFILE "
            "prefix, a phenotype CSV with the required Fast3VmrMLM header, and a Q/structure CSV."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bfile_prefix": {
                    "type": "string",
                    "description": (
                        "Input PLINK BFILE prefix. The files <prefix>.bed, <prefix>.bim, and "
                        "<prefix>.fam must exist. Example prefix:\n"
                        "/home/wlg/MyFiles/Project/data/1.GWAS/maize976\n"
                        "Example .fam rows:\n"
                        "CIMBL32_X_ZHENG58 CIMBL32_X_ZHENG58 0 0 0 -9\n"
                        "CIMBL32_X_MO17 CIMBL32_X_MO17 0 0 0 -9\n"
                        "CIMBL89_X_ZHENG58 CIMBL89_X_ZHENG58 0 0 0 -9\n"
                        "CIMBL89_X_MO17 CIMBL89_X_MO17 0 0 0 -9"
                    ),
                },
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Phenotype CSV with the Fast3VmrMLM phenotype ID header in the first "
                        "column and one or more trait-environment columns. Example:\n"
                        "<Phenotype>,trait1_env1,trait1_env2,trait1_env3,trait1_env4\n"
                        "04K5686_X_MO17,275.8,254.6,235.2,232.2\n"
                        "04K5686_X_ZHENG58,222,229.4,218,214.4\n"
                        "04K5702_X_MO17,247.5,245.5,188.75,206.75\n"
                        "05W002_X_MO17,268,278.6,240,238.25"
                    ),
                },
                "structure_csv": {
                    "type": "string",
                    "description": (
                        "Population-structure/Q CSV with the Fast3VmrMLM structure ID header in "
                        "the first column. Example:\n"
                        "<Structure>,Q1\n"
                        "04K5686_X_MO17,0.051944\n"
                        "04K5686_X_ZHENG58,0.931830\n"
                        "04K5702_X_MO17,0.082082\n"
                        "05W002_X_MO17,0.059069"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/qei_detection/."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional output file prefix path used as fileOut in Fast3VmrMLM. "
                        "Defaults to <output_dir>/res."
                    ),
                },
                "trait_count": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Trait count passed as trait=. Defaults to 1.",
                },
                "n_en": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1},
                    "description": (
                        "Environment-count vector passed as n_en=c(...). Defaults to [4] when "
                        "trait_count is 1."
                    ),
                },
                "phenotype_id_column": {
                    "type": "string",
                    "description": "Required first-column header in phenotype_csv. Defaults to '<Phenotype>'.",
                },
                "structure_id_column": {
                    "type": "string",
                    "description": "Required first-column header in structure_csv. Defaults to '<Structure>'.",
                },
                "geno_type": {
                    "type": "string",
                    "description": "genoType passed to Fast3VmrMLM_MEJA. Defaults to 'SNP'.",
                },
                "svrad": {
                    "type": "number",
                    "description": "svrad parameter. Defaults to 20000.",
                },
                "svpal": {
                    "type": "number",
                    "description": "svpal parameter. Defaults to 0.01.",
                },
                "svmlod": {
                    "type": "number",
                    "description": "svmlod parameter. Defaults to 3.",
                },
                "n_threads": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Thread count passed as nThreads=. Defaults to 10.",
                },
                "draw_plot": {
                    "type": "boolean",
                    "description": "Whether to request Manhattan TIFF plots. Defaults to false.",
                },
                "plot_format": {
                    "type": "string",
                    "description": "Plotformat string passed to Fast3VmrMLM_MEJA. Defaults to '*.tiff'.",
                },
            },
            "required": ["bfile_prefix", "phenotype_csv", "structure_csv"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        phenotype_csv: str,
        structure_csv: str,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        trait_count: int | None = None,
        n_en: list[int] | None = None,
        phenotype_id_column: str | None = None,
        structure_id_column: str | None = None,
        geno_type: str | None = None,
        svrad: float | None = None,
        svpal: float | None = None,
        svmlod: float | None = None,
        n_threads: int | None = None,
        draw_plot: bool | None = None,
        plot_format: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                phenotype_csv=phenotype_csv,
                structure_csv=structure_csv,
                output_dir=output_dir,
                output_prefix=output_prefix,
                trait_count=trait_count,
                n_en=n_en,
                phenotype_id_column=phenotype_id_column,
                structure_id_column=structure_id_column,
                geno_type=geno_type,
                svrad=svrad,
                svpal=svpal,
                svmlod=svmlod,
                n_threads=n_threads,
                draw_plot=draw_plot,
                plot_format=plot_format,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: QEI detection failed.\n"
                f"- BFILE prefix: {prepared.bfile_prefix_path}\n"
                f"- Phenotype CSV: {prepared.phenotype_csv_path}\n"
                f"- Structure CSV: {prepared.structure_csv_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "QEI detection completed.",
            f"- Launcher: {prepared.launcher}",
            f"- BFILE prefix: {prepared.bfile_prefix_path}",
            f"- Phenotype CSV: {prepared.phenotype_csv_path}",
            f"- Structure CSV: {prepared.structure_csv_path}",
            f"- Output prefix: {prepared.output_prefix_path}",
            f"- Trait count: {prepared.trait_count}",
            f"- n_en: {prepared.n_en}",
            f"- Pre-kinship CSV: {prepared.prekinship_path}",
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
        bfile_prefix: str,
        phenotype_csv: str,
        structure_csv: str,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        trait_count: int | None = None,
        n_en: list[int] | None = None,
        phenotype_id_column: str | None = None,
        structure_id_column: str | None = None,
        geno_type: str | None = None,
        svrad: float | None = None,
        svpal: float | None = None,
        svmlod: float | None = None,
        n_threads: int | None = None,
        draw_plot: bool | None = None,
        plot_format: str | None = None,
    ) -> PreparedQeiDetectionRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv, "Phenotype CSV")
        structure_csv_path = self._resolve_csv_file(structure_csv, "Structure CSV")

        trait_count_value = int(trait_count if trait_count is not None else 1)
        if trait_count_value < 1:
            raise ValueError("trait_count must be >= 1")
        n_en_value = self._normalize_n_en(n_en, trait_count_value)
        phenotype_id_column_value = self._normalize_column_name(
            phenotype_id_column or "<Phenotype>",
            "phenotype_id_column",
        )
        structure_id_column_value = self._normalize_column_name(
            structure_id_column or "<Structure>",
            "structure_id_column",
        )
        geno_type_value = (geno_type or "SNP").strip() or "SNP"
        svrad_value = float(svrad if svrad is not None else 2e4)
        svpal_value = float(svpal if svpal is not None else 1e-2)
        svmlod_value = float(svmlod if svmlod is not None else 3)
        n_threads_value = int(n_threads if n_threads is not None else 10)
        draw_plot_value = bool(draw_plot) if draw_plot is not None else False
        plot_format_value = (plot_format or "*.tiff").strip() or "*.tiff"

        if svrad_value <= 0:
            raise ValueError("svrad must be > 0")
        if svpal_value <= 0:
            raise ValueError("svpal must be > 0")
        if svmlod_value <= 0:
            raise ValueError("svmlod must be > 0")
        if n_threads_value < 1:
            raise ValueError("n_threads must be >= 1")

        phenotype_header = self._read_csv_header(phenotype_csv_path, "Phenotype CSV")
        structure_header = self._read_csv_header(structure_csv_path, "Structure CSV")
        if phenotype_header[0] != phenotype_id_column_value:
            raise ValueError(
                f"Phenotype CSV first column must be {phenotype_id_column_value}: {phenotype_csv_path}"
            )
        if structure_header[0] != structure_id_column_value:
            raise ValueError(
                f"Structure CSV first column must be {structure_id_column_value}: {structure_csv_path}"
            )
        if len(phenotype_header) - 1 < sum(n_en_value):
            raise ValueError(
                "Phenotype CSV has fewer trait-environment columns than the requested n_en sum"
            )
        if len(structure_header) < 2:
            raise ValueError(f"Structure CSV must contain at least one Q column: {structure_csv_path}")

        output_root = self._resolve_output_dir(output_dir)
        output_prefix_path = self._resolve_output_prefix(output_prefix, output_root)
        prekinship_path = Path(f"{output_prefix_path}preKinship.csv")
        midresult_paths = [
            Path(f"{output_prefix_path}trait_{index}_midresult.csv")
            for index in range(1, trait_count_value + 1)
        ]
        result_xlsx_paths = [
            Path(f"{output_prefix_path}trait_{index}_result.xlsx")
            for index in range(1, trait_count_value + 1)
        ]
        summary_path = output_prefix_path.parent / f"{output_prefix_path.name}_qei_detection_summary.txt"

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
            "--bfile-prefix",
            str(bfile_prefix_path),
            "--phenotype-csv",
            str(phenotype_csv_path),
            "--structure-csv",
            str(structure_csv_path),
            "--output-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--trait-count",
            str(trait_count_value),
            "--n-en",
            ",".join(str(item) for item in n_en_value),
            "--phenotype-id-column",
            phenotype_id_column_value,
            "--structure-id-column",
            structure_id_column_value,
            "--geno-type",
            geno_type_value,
            "--svrad",
            str(svrad_value),
            "--svpal",
            str(svpal_value),
            "--svmlod",
            str(svmlod_value),
            "--n-threads",
            str(n_threads_value),
            "--draw-plot",
            "TRUE" if draw_plot_value else "FALSE",
            "--plot-format",
            plot_format_value,
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedQeiDetectionRun(
            launcher=env_status["launcher"],
            phenotype_id_column=phenotype_id_column_value,
            structure_id_column=structure_id_column_value,
            trait_count=trait_count_value,
            n_en=n_en_value,
            geno_type=geno_type_value,
            svrad=svrad_value,
            svpal=svpal_value,
            svmlod=svmlod_value,
            n_threads=n_threads_value,
            draw_plot=draw_plot_value,
            plot_format=plot_format_value,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            phenotype_csv_path=phenotype_csv_path,
            structure_csv_path=structure_csv_path,
            output_dir=output_prefix_path.parent,
            output_prefix_path=output_prefix_path,
            prekinship_path=prekinship_path,
            midresult_paths=midresult_paths,
            result_xlsx_paths=result_xlsx_paths,
            summary_path=summary_path,
        )

    def _resolve_csv_file(self, value: str, label: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"{label} not found: {path}")
        if not path.is_file():
            raise ValueError(f"{label} must be a file: {path}")
        if path.suffix.lower() != ".csv":
            raise ValueError(f"{label} must end with .csv: {path}")
        return path

    def _resolve_output_prefix(self, value: str | None, output_root: Path) -> Path:
        if value:
            raw = Path(value).expanduser()
            if raw.is_absolute():
                return _resolve_path(str(raw), self.allowed_dir)
            return _resolve_path(str(output_root / raw), self.allowed_dir)
        return output_root / "res"

    def _read_csv_header(self, path: Path, label: str) -> list[str]:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"{label} is empty: {path}") from exc
        header = [item.strip() for item in header]
        if len(header) < 2:
            raise ValueError(f"{label} must contain at least two columns: {path}")
        return header

    def _normalize_column_name(self, value: str, field_name: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise ValueError(f"{field_name} must not be empty")
        if "/" in candidate or "\\" in candidate:
            raise ValueError(f"{field_name} must not contain path separators: {candidate}")
        return candidate

    def _normalize_n_en(self, n_en: list[int] | None, trait_count: int) -> list[int]:
        if n_en is None:
            if trait_count != 1:
                raise ValueError("n_en must be provided when trait_count is not 1")
            return [4]
        values = [int(item) for item in n_en]
        if not values:
            raise ValueError("n_en must contain at least one positive integer")
        if any(item < 1 for item in values):
            raise ValueError("n_en values must be >= 1")
        if len(values) != trait_count:
            raise ValueError("n_en length must match trait_count")
        return values
