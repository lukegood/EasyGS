"""GWAS analysis tool backed by rMVP."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedGwasRun:
    """Prepared execution plan for GWAS analysis."""

    launcher: str
    line_column: str
    trait_column: str
    methods: list[str]
    threshold: float
    pcs_keep: int
    npc_glm: int
    npc_mlm: int
    npc_farmcpu: int
    ncpus: int
    command: list[str]
    bfile_prefix_path: Path
    phenotype_csv_path: Path
    output_dir: Path
    summary_path: Path
    result_prefix: str
    mvp_prefix_path: Path
    kinship_prefix_path: Path
    pc_prefix_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "line_column": self.line_column,
            "trait_column": self.trait_column,
            "methods": list(self.methods),
            "threshold": self.threshold,
            "pcs_keep": self.pcs_keep,
            "npc_glm": self.npc_glm,
            "npc_mlm": self.npc_mlm,
            "npc_farmcpu": self.npc_farmcpu,
            "ncpus": self.ncpus,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "output_dir": str(self.output_dir),
            "summary_path": str(self.summary_path),
            "result_prefix": self.result_prefix,
            "mvp_prefix_path": str(self.mvp_prefix_path),
            "kinship_prefix_path": str(self.kinship_prefix_path),
            "pc_prefix_path": str(self.pc_prefix_path),
            "notes": list(self.notes),
        }



class RunGwasTool(PlinkToolBase, Tool):
    """Run rMVP GWAS from a PLINK BFILE and phenotype CSV."""

    _ALLOWED_METHODS = ("GLM", "MLM", "FarmCPU")

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="gwas_analysis",
            default_output_subdir="gwas",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "gwas.sh"
        self.r_script_path = self.skill_dir / "run_gwas.R"
        self.summary_script_path = self.skill_dir / "summarize_gwas.py"

    @property
    def name(self) -> str:
        return "run_gwas"

    @property
    def description(self) -> str:
        return (
            "Run rMVP GWAS in EasyGS_1 from a PLINK BFILE prefix and a two-column phenotype "
            "CSV, then internally derive kinship/PC files and export GWAS result CSVs and plots."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bfile_prefix": {
                    "type": "string",
                    "description": (
                        "Input PLINK BFILE prefix. The files <prefix>.bed, <prefix>.bim, "
                        "and <prefix>.fam must exist. Example prefix: "
                        "/home/wlg/MyFiles/Project/data/1.GWAS/maize976\n"
                        "Example .fam rows:\n"
                        "CIMBL32_X_ZHENG58 CIMBL32_X_ZHENG58 0 0 0 -9\n"
                        "CIMBL32_X_MO17 CIMBL32_X_MO17 0 0 0 -9\n"
                        "CIMBL89_X_ZHENG58 CIMBL89_X_ZHENG58 0 0 0 -9\n"
                        "Example .bim rows:\n"
                        "1 chr1.s_2356 0 2356 C T\n"
                        "1 chr1.s_146037 0 146037 T C\n"
                        "1 chr1.s_203657 0 203657 C T"
                    ),
                },
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Phenotype CSV containing one line-ID column and one trait column. "
                        "Example:\n"
                        "LINE,intercept\n"
                        "04K5686_X_MO17,-1.10711819539\n"
                        "04K5686_X_ZHENG58,-11.2907298480106\n"
                        "04K5702_X_MO17,-30.5423512439191\n"
                        "05W002_X_MO17,9.20605204500537"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/gwas/."
                    ),
                },
                "line_column": {
                    "type": "string",
                    "description": (
                        "Line-ID column name in phenotype_csv. Defaults to the first CSV column."
                    ),
                },
                "trait_column": {
                    "type": "string",
                    "description": (
                        "Trait column name in phenotype_csv. Defaults to the second CSV column. "
                        "This name also becomes the GWAS output prefix, for example 'intercept'."
                    ),
                },
                "methods": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(self._ALLOWED_METHODS),
                    },
                    "description": (
                        "GWAS models to run. Defaults to ['GLM', 'MLM', 'FarmCPU']."
                    ),
                },
                "threshold": {
                    "type": "number",
                    "description": "Significance threshold passed to rMVP. Defaults to 0.05.",
                },
                "pcs_keep": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Number of PCs to calculate with MVP.Data.PC. Defaults to 5.",
                },
                "npc_glm": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of computed PCs passed into CV.GLM. Defaults to pcs_keep.",
                },
                "npc_mlm": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of computed PCs passed into CV.MLM. Defaults to pcs_keep.",
                },
                "npc_farmcpu": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Number of computed PCs passed into FarmCPU as CV.FarmCPU. "
                        "Defaults to pcs_keep."
                    ),
                },
                "ncpus": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "CPU count passed to rMVP. Defaults to 10.",
                },
            },
            "required": ["bfile_prefix", "phenotype_csv"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        phenotype_csv: str,
        output_dir: str | None = None,
        line_column: str | None = None,
        trait_column: str | None = None,
        methods: list[str] | None = None,
        threshold: float | None = None,
        pcs_keep: int | None = None,
        npc_glm: int | None = None,
        npc_mlm: int | None = None,
        npc_farmcpu: int | None = None,
        ncpus: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                phenotype_csv=phenotype_csv,
                output_dir=output_dir,
                line_column=line_column,
                trait_column=trait_column,
                methods=methods,
                threshold=threshold,
                pcs_keep=pcs_keep,
                npc_glm=npc_glm,
                npc_mlm=npc_mlm,
                npc_farmcpu=npc_farmcpu,
                ncpus=ncpus,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: GWAS analysis failed.\n"
                f"- BFILE prefix: {prepared.bfile_prefix_path}\n"
                f"- Phenotype CSV: {prepared.phenotype_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "GWAS analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- BFILE prefix: {prepared.bfile_prefix_path}",
            f"- Phenotype CSV: {prepared.phenotype_csv_path}",
            f"- Trait column: {prepared.trait_column}",
            f"- Methods: {', '.join(prepared.methods)}",
            f"- MVP prefix: {prepared.mvp_prefix_path}",
            f"- Kinship prefix: {prepared.kinship_prefix_path}",
            f"- PC prefix: {prepared.pc_prefix_path}",
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
        bfile_prefix: str,
        phenotype_csv: str,
        output_dir: str | None = None,
        line_column: str | None = None,
        trait_column: str | None = None,
        methods: list[str] | None = None,
        threshold: float | None = None,
        pcs_keep: int | None = None,
        npc_glm: int | None = None,
        npc_mlm: int | None = None,
        npc_farmcpu: int | None = None,
        ncpus: int | None = None,
    ) -> PreparedGwasRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv)
        output_root = self._resolve_output_dir(output_dir)

        header = self._read_csv_header(phenotype_csv_path)
        line_column_value = self._normalize_column_name(
            line_column or self._default_line_column(header),
            "line_column",
        )
        trait_column_value = self._normalize_column_name(
            trait_column or self._default_trait_column(header),
            "trait_column",
        )
        if line_column_value == trait_column_value:
            raise ValueError("line_column and trait_column must be different")
        if line_column_value not in header:
            raise ValueError(f"line_column not found in phenotype CSV: {line_column_value}")
        if trait_column_value not in header:
            raise ValueError(f"trait_column not found in phenotype CSV: {trait_column_value}")

        methods_value = self._normalize_methods(methods)
        threshold_value = float(threshold if threshold is not None else 0.05)
        pcs_keep_value = int(pcs_keep if pcs_keep is not None else 5)
        npc_glm_value = int(npc_glm if npc_glm is not None else pcs_keep_value)
        npc_mlm_value = int(npc_mlm if npc_mlm is not None else pcs_keep_value)
        npc_farmcpu_value = int(npc_farmcpu if npc_farmcpu is not None else pcs_keep_value)
        ncpus_value = int(ncpus if ncpus is not None else 10)
        if threshold_value <= 0:
            raise ValueError("threshold must be > 0")
        if pcs_keep_value < 1:
            raise ValueError("pcs_keep must be >= 1")
        if min(npc_glm_value, npc_mlm_value, npc_farmcpu_value) < 0:
            raise ValueError("npc_glm, npc_mlm, and npc_farmcpu must be >= 0")
        if ncpus_value < 1:
            raise ValueError("ncpus must be >= 1")

        result_prefix = trait_column_value
        summary_path = output_root / f"{result_prefix}_gwas_summary.txt"
        mvp_prefix_path = output_root / "mvp.plink"
        kinship_prefix_path = output_root / "mvpKin"
        pc_prefix_path = output_root / "mvpPC"

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
            "--output-dir",
            str(output_root),
            "--summary-output",
            str(summary_path),
            "--line-column",
            line_column_value,
            "--trait-column",
            trait_column_value,
            "--methods",
            ",".join(methods_value),
            "--threshold",
            str(threshold_value),
            "--pcs-keep",
            str(pcs_keep_value),
            "--npc-glm",
            str(npc_glm_value),
            "--npc-mlm",
            str(npc_mlm_value),
            "--npc-farmcpu",
            str(npc_farmcpu_value),
            "--ncpus",
            str(ncpus_value),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedGwasRun(
            launcher=env_status["launcher"],
            line_column=line_column_value,
            trait_column=trait_column_value,
            methods=methods_value,
            threshold=threshold_value,
            pcs_keep=pcs_keep_value,
            npc_glm=npc_glm_value,
            npc_mlm=npc_mlm_value,
            npc_farmcpu=npc_farmcpu_value,
            ncpus=ncpus_value,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            phenotype_csv_path=phenotype_csv_path,
            output_dir=output_root,
            summary_path=summary_path,
            result_prefix=result_prefix,
            mvp_prefix_path=mvp_prefix_path,
            kinship_prefix_path=kinship_prefix_path,
            pc_prefix_path=pc_prefix_path,
        )

    def _resolve_csv_file(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"Input CSV not found: {path}")
        if not path.is_file():
            raise ValueError(f"Input CSV must be a file: {path}")
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Input CSV must end with .csv: {path}")
        return path

    def _read_csv_header(self, path: Path) -> list[str]:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"Phenotype CSV is empty: {path}") from exc
        header = [item.strip() for item in header]
        if len(header) < 2:
            raise ValueError(f"Phenotype CSV must contain at least two columns: {path}")
        return header

    def _default_line_column(self, header: list[str]) -> str:
        return header[0]

    def _default_trait_column(self, header: list[str]) -> str:
        return header[1]

    def _normalize_column_name(self, value: str, field_name: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            raise ValueError(f"{field_name} must not be empty")
        if "/" in candidate or "\\" in candidate:
            raise ValueError(f"{field_name} must not contain path separators: {candidate}")
        return candidate

    def _normalize_methods(self, methods: list[str] | None) -> list[str]:
        items = methods or list(self._ALLOWED_METHODS)
        normalized: list[str] = []
        for item in items:
            candidate = str(item).strip()
            if not candidate:
                continue
            if candidate not in self._ALLOWED_METHODS:
                raise ValueError(
                    f"Unsupported GWAS method: {candidate}. Allowed values: {', '.join(self._ALLOWED_METHODS)}"
                )
            if candidate not in normalized:
                normalized.append(candidate)
        if not normalized:
            raise ValueError("methods must contain at least one GWAS method")
        return normalized
