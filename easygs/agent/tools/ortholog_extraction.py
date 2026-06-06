"""Ortholog row extraction tool based on an explicit gene list and ortholog matrix TSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedOrthologExtractionRun:
    """Prepared execution plan for ortholog extraction."""

    launcher: str
    command: list[str]
    genelist_txt_path: Path
    ortholog_matrix_tsv_path: Path
    output_dir: Path
    output_tsv_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "genelist_txt_path": str(self.genelist_txt_path),
            "ortholog_matrix_tsv_path": str(self.ortholog_matrix_tsv_path),
            "output_dir": str(self.output_dir),
            "output_tsv_path": str(self.output_tsv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunOrthologExtractionTool(PlinkToolBase, Tool):
    """Extract ortholog rows that match a user-provided gene list."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="ortholog_extraction_analysis",
            default_output_subdir="ortholog_extraction",
            env_name="EasyGS_2",
        )
        self.script_path = self.skill_dir / "ortholog_extraction.sh"
        self.summary_script_path = self.skill_dir / "summarize_ortholog_extraction.py"

    @property
    def name(self) -> str:
        return "run_ortholog_extraction"

    @property
    def description(self) -> str:
        return (
            "Extract ortholog rows in EasyGS_2 from a user-provided gene list TXT and a "
            "user-provided maize ortholog matrix TSV, then export a matched .ortholog.tsv file."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "genelist_txt": {
                    "type": "string",
                    "description": (
                        "User-provided gene list TXT with one maize gene ID per line. Example:\n"
                        "Zm00001d031939\n"
                        "Zm00001d031940\n"
                        "Zm00001d031941\n"
                        "Zm00001d031942"
                    ),
                },
                "ortholog_matrix_tsv": {
                    "type": "string",
                    "description": (
                        "User-provided maize ortholog matrix TSV. Example:\n"
                        "Maize\tArabidopsis\tsorghum\tBrachypodium\trice\tsetaria\n"
                        "GRMZM5G800096\tATCG01050\tABK79546,SORBI_K036300\tNA\tNA\tSi020851m.g\n"
                        "GRMZM5G800101\tNA\tABK79539\tBRADI4G37052\tOS04G0473025\tNA\n"
                        "GRMZM5G800457\tNA\tNA\tNA\tNA\tSi020789m.g"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Default: workspace/default_results/ortholog_extraction/. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "output_filename": {
                    "type": "string",
                    "description": (
                        "Optional output filename. Default: <genelist_stem>.ortholog.tsv, for example "
                        "genelist.txt -> genelist.ortholog.tsv. If you want to override it, please "
                        "provide it explicitly."
                    ),
                },
            },
            "required": ["genelist_txt", "ortholog_matrix_tsv"],
        }

    async def execute(
        self,
        genelist_txt: str,
        ortholog_matrix_tsv: str,
        output_dir: str | None = None,
        output_filename: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                genelist_txt=genelist_txt,
                ortholog_matrix_tsv=ortholog_matrix_tsv,
                output_dir=output_dir,
                output_filename=output_filename,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Ortholog extraction failed.\n"
                f"- Gene list TXT: {prepared.genelist_txt_path}\n"
                f"- Ortholog matrix TSV: {prepared.ortholog_matrix_tsv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Ortholog extraction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Gene list TXT: {prepared.genelist_txt_path}",
            f"- Ortholog matrix TSV: {prepared.ortholog_matrix_tsv_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Ortholog TSV: {prepared.output_tsv_path}",
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
        genelist_txt: str,
        ortholog_matrix_tsv: str,
        output_dir: str | None = None,
        output_filename: str | None = None,
    ) -> PreparedOrthologExtractionRun:
        genelist_txt_path = self._resolve_text_file(genelist_txt, "Gene list TXT")
        ortholog_matrix_tsv_path = self._resolve_text_file(
            ortholog_matrix_tsv,
            "Ortholog matrix TSV",
        )

        self._validate_non_empty_lines(genelist_txt_path, "Gene list TXT")
        self._validate_tabular_preview(ortholog_matrix_tsv_path, min_columns=2, label="Ortholog matrix TSV")

        output_root = self._resolve_output_dir(output_dir)
        output_filename_value = self._resolve_output_filename(output_filename, genelist_txt_path)
        output_tsv_path = output_root / output_filename_value
        summary_path = output_root / f"{output_tsv_path.stem}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["grep", "python3"])
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
            "--genelist-txt",
            str(genelist_txt_path),
            "--ortholog-matrix-tsv",
            str(ortholog_matrix_tsv_path),
            "--output-tsv",
            str(output_tsv_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedOrthologExtractionRun(
            launcher=env_status["launcher"],
            command=command,
            genelist_txt_path=genelist_txt_path,
            ortholog_matrix_tsv_path=ortholog_matrix_tsv_path,
            output_dir=output_root,
            output_tsv_path=output_tsv_path,
            summary_path=summary_path,
        )

    def _resolve_text_file(self, value: str | None, label: str) -> Path:
        if not value:
            raise ValueError(f"{label} is required.")
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"{label} not found: {path}")
        if not path.is_file():
            raise ValueError(f"{label} must be a file: {path}")
        return path

    def _resolve_output_filename(self, value: str | None, genelist_txt_path: Path) -> str:
        default_name = f"{genelist_txt_path.stem}.ortholog.tsv"
        candidate = (value or "").strip()
        if not candidate:
            return default_name
        resolved_name = Path(candidate).name.strip()
        return resolved_name or default_name

    def _validate_non_empty_lines(self, path: Path, label: str) -> None:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        if not lines:
            raise ValueError(f"{label} is empty: {path}")

    def _validate_tabular_preview(self, path: Path, min_columns: int, label: str) -> None:
        valid_rows = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip("\n")
                if not line.strip():
                    continue
                if len(line.split("\t")) < min_columns:
                    raise ValueError(
                        f"{label} must be tab-delimited with at least {min_columns} columns: {path}"
                    )
                valid_rows += 1
                if valid_rows >= 3:
                    break
        if valid_rows == 0:
            raise ValueError(f"{label} is empty: {path}")
