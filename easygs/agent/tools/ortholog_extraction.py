"""Ortholog row extraction tool based on an explicit gene list and ortholog matrix TSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path

_SPECIES_MATRIX_FILENAMES = {
    "maize": "maize_ortholog_matrix.tsv",
    "wheat": "wheat_ortholog_matrix.tsv",
    "rice": "rice_ortholog_matrix.tsv",
}


@dataclass
class PreparedOrthologExtractionRun:
    """Prepared execution plan for ortholog extraction."""

    launcher: str
    species: str
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
            "species": self.species,
            "genelist_txt_path": str(self.genelist_txt_path),
            "ortholog_matrix_tsv_path": str(self.ortholog_matrix_tsv_path),
            "output_dir": str(self.output_dir),
            "output_tsv_path": str(self.output_tsv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }


class RunOrthologExtractionTool(PlinkToolBase, Tool):
    """Extract species ortholog rows that exactly match a user-provided gene list."""

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
        self.extraction_script_path = self.skill_dir / "extract_orthologs.py"
        self.summary_script_path = self.skill_dir / "summarize_ortholog_extraction.py"
        self.matrix_resource_paths = {
            species: resolve_user_resource_path("ortholog_extraction_analysis", filename)
            for species, filename in _SPECIES_MATRIX_FILENAMES.items()
        }

    @property
    def name(self) -> str:
        return "run_ortholog_extraction"

    @property
    def description(self) -> str:
        return (
            "Extract ortholog rows for maize, wheat, or rice in EasyGS_2 from a user-provided "
            "gene list. The species matrix is selected from EasyGS resources and matched "
            "exactly against its first column."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "genelist_txt": {
                    "type": "string",
                    "description": (
                        "User-provided gene list TXT with one gene ID per line. Example for "
                        "wheat:\n"
                        "TraesCS6A03G0926000\n"
                        "TraesCS3D03G0591600\n"
                        "TraesCS3B03G0806700\n"
                        "TraesCS1D03G0346300"
                    ),
                },
                "species": {
                    "type": "string",
                    "enum": ["maize", "wheat", "rice"],
                    "default": "maize",
                    "description": (
                        "Source species for the requested genes: maize, wheat, or rice. "
                        "Default: maize. The matching ortholog matrix is resolved automatically "
                        "from ~/.easygs/resources/ortholog_extraction_analysis/."
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
                        "Optional output filename. Default: <genelist_stem>.ortholog.tsv; a "
                        "trailing _genes is removed, so 100_wheat_genes.txt becomes "
                        "100_wheat.ortholog.tsv."
                    ),
                },
            },
            "required": ["genelist_txt"],
        }

    async def execute(
        self,
        genelist_txt: str,
        species: str = "maize",
        output_dir: str | None = None,
        output_filename: str | None = None,
        **kwargs: Any,
    ) -> str:
        if kwargs.get("ortholog_matrix_tsv"):
            return (
                "Error: ortholog_matrix_tsv is no longer a public parameter for "
                "ortholog_extraction_analysis. Select species=maize, wheat, or rice; EasyGS "
                "will use the matching resource."
            )
        try:
            prepared = await self.prepare_run(
                genelist_txt=genelist_txt,
                species=species,
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
                f"- Species: {prepared.species}\n"
                f"- Gene list TXT: {prepared.genelist_txt_path}\n"
                f"- Ortholog matrix TSV: {prepared.ortholog_matrix_tsv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Ortholog extraction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Species: {prepared.species}",
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
        species: str = "maize",
        output_dir: str | None = None,
        output_filename: str | None = None,
    ) -> PreparedOrthologExtractionRun:
        species_value = self._normalize_species(species)
        genelist_txt_path = self._resolve_text_file(genelist_txt, "Gene list TXT")
        ortholog_matrix_tsv_path = self._resolve_matrix_resource(species_value)

        self._validate_non_empty_lines(genelist_txt_path, "Gene list TXT")
        self._validate_matrix(ortholog_matrix_tsv_path, species_value)

        output_root = self._resolve_output_dir(output_dir)
        output_filename_value = self._resolve_output_filename(output_filename, genelist_txt_path)
        output_tsv_path = output_root / output_filename_value
        summary_path = output_root / f"{output_tsv_path.stem}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "extraction script": self.extraction_script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["python3"])
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
            "--species",
            species_value,
            "--ortholog-matrix-tsv",
            str(ortholog_matrix_tsv_path),
            "--output-tsv",
            str(output_tsv_path),
            "--summary-output",
            str(summary_path),
            "--extraction-script",
            str(self.extraction_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedOrthologExtractionRun(
            launcher=env_status["launcher"],
            species=species_value,
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

    def _normalize_species(self, value: str) -> str:
        species = str(value).strip().lower()
        if species not in _SPECIES_MATRIX_FILENAMES:
            allowed = ", ".join(_SPECIES_MATRIX_FILENAMES)
            raise ValueError(f"species must be one of: {allowed}")
        return species

    def _resolve_matrix_resource(self, species: str) -> Path:
        filename = _SPECIES_MATRIX_FILENAMES[species]
        path = self.matrix_resource_paths[species]
        if not path.exists():
            raise ValueError(
                "Missing required resource for ortholog_extraction_analysis:\n"
                f"{path}\n\n"
                f"Please prepare {filename} and place it at the path above. Set "
                "EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if not path.is_file():
            raise ValueError(f"Ortholog matrix resource must be a file: {path}")
        return path

    def _resolve_output_filename(self, value: str | None, genelist_txt_path: Path) -> str:
        default_stem = genelist_txt_path.stem
        if default_stem.endswith("_genes"):
            default_stem = default_stem[: -len("_genes")]
        default_name = f"{default_stem}.ortholog.tsv"
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

    def _validate_matrix(self, path: Path, species: str) -> None:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.rstrip("\r\n")
                if not line.strip():
                    continue
                fields = line.split("\t")
                if len(fields) < 2:
                    raise ValueError(
                        f"Ortholog matrix must be tab-delimited with at least 2 columns: {path}"
                    )
                source_header = fields[0].lstrip("\ufeff").strip().lower()
                if source_header != species:
                    raise ValueError(
                        f"Ortholog matrix first header must be {species.title()!r}, found "
                        f"{fields[0]!r}: {path}"
                    )
                return
        raise ValueError(f"Ortholog matrix is empty: {path}")
