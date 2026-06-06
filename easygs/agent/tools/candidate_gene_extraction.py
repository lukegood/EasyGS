"""Candidate gene extraction tool based on LD-window expansion and bedtools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedCandidateGeneExtractionRun:
    """Prepared execution plan for candidate gene extraction."""

    launcher: str
    ld_distance: int
    command: list[str]
    bed_path: Path
    gene_bed_path: Path
    output_dir: Path
    extended_bed_path: Path
    gene_list_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "ld_distance": self.ld_distance,
            "bed_path": str(self.bed_path),
            "gene_bed_path": str(self.gene_bed_path),
            "output_dir": str(self.output_dir),
            "extended_bed_path": str(self.extended_bed_path),
            "gene_list_path": str(self.gene_list_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunCandidateGeneExtractionTool(PlinkToolBase, Tool):
    """Extract candidate genes within an LD-expanded BED interval set."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="candidate_gene_extraction_analysis",
            default_output_subdir="candidate_gene_extraction",
            env_name="EasyGS_2",
        )
        self.script_path = self.skill_dir / "candidate_gene_extraction.sh"
        self.summary_script_path = self.skill_dir / "summarize_candidate_gene_extraction.py"

    @property
    def name(self) -> str:
        return "run_candidate_gene_extraction"

    @property
    def description(self) -> str:
        return (
            "Run candidate gene extraction in EasyGS_2 by expanding a user-provided BED file "
            "with an LD distance, intersecting it with gene annotations, and exporting genelist.txt."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bed": {
                    "type": "string",
                    "description": (
                        "User-provided BED file containing loci to expand. Example:\n"
                        "1\t207606062\t207606063\n"
                        "2\t180017154\t180017155\n"
                        "2\t191156851\t191156852\n"
                        "2\t195873477\t195873478"
                    ),
                },
                "ld_distance": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Optional LD expansion distance in bp. Default: 50000. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
                "gene_bed": {
                    "type": "string",
                    "description": (
                        "User-provided gene interval BED file with gene IDs in column 4. Example:\n"
                        "1\t44288\t49837\tZm00001d027230\n"
                        "1\t50876\t55716\tZm00001d027231\n"
                        "1\t92298\t95134\tZm00001d027232\n"
                        "1\t111654\t118312\tZm00001d027233"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Defaults to "
                        "workspace/default_results/candidate_gene_extraction/. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
            },
            "required": ["bed", "gene_bed"],
        }

    async def execute(
        self,
        bed: str,
        gene_bed: str,
        ld_distance: int | None = None,
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bed=bed,
                ld_distance=ld_distance,
                gene_bed=gene_bed,
                output_dir=output_dir,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Candidate gene extraction failed.\n"
                f"- BED: {prepared.bed_path}\n"
                f"- LD distance: {prepared.ld_distance}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Candidate gene extraction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- BED: {prepared.bed_path}",
            f"- LD distance: {prepared.ld_distance}bp",
            f"- Gene annotation BED: {prepared.gene_bed_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Extended BED: {prepared.extended_bed_path}",
            f"- Gene list: {prepared.gene_list_path}",
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
        bed: str,
        gene_bed: str,
        ld_distance: int | None = None,
        output_dir: str | None = None,
    ) -> PreparedCandidateGeneExtractionRun:
        bed_path = self._resolve_bed_file(bed)
        self._validate_bed_preview(bed_path)
        output_root = self._resolve_output_dir(output_dir)

        ld_distance_value = int(ld_distance if ld_distance is not None else 50000)
        if ld_distance_value < 0:
            raise ValueError("ld_distance must be >= 0")

        gene_bed_path = self._resolve_gene_bed(gene_bed)

        extended_bed_path = output_root / f"{bed_path.stem}.extend.bed"
        gene_list_path = output_root / "genelist.txt"
        summary_path = output_root / "genelist_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["bedtools", "python3", "awk"])
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
            "--bed",
            str(bed_path),
            "--ld-distance",
            str(ld_distance_value),
            "--extended-bed-output",
            str(extended_bed_path),
            "--gene-list-output",
            str(gene_list_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--gene-bed",
            str(gene_bed_path),
        ]

        return PreparedCandidateGeneExtractionRun(
            launcher=env_status["launcher"],
            ld_distance=ld_distance_value,
            command=command,
            bed_path=bed_path,
            gene_bed_path=gene_bed_path,
            output_dir=output_root,
            extended_bed_path=extended_bed_path,
            gene_list_path=gene_list_path,
            summary_path=summary_path,
        )

    def _resolve_bed_file(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"BED file not found: {path}")
        if not path.is_file():
            raise ValueError(f"BED input must be a file: {path}")
        if path.suffix.lower() != ".bed":
            raise ValueError(f"BED input must end with .bed: {path}")
        return path

    def _resolve_gene_bed(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        self._validate_gene_bed_preview(path)
        return path

    def _validate_bed_preview(self, path: Path) -> None:
        valid_rows = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    raise ValueError(f"BED file must have at least 3 tab-separated columns: {path}")
                try:
                    int(parts[1])
                    int(parts[2])
                except ValueError as exc:
                    raise ValueError(f"BED start/end columns must be integers: {path}") from exc
                valid_rows += 1
                if valid_rows >= 3:
                    break
        if valid_rows == 0:
            raise ValueError(f"BED file does not contain any valid data rows: {path}")

    def _validate_gene_bed_preview(self, path: Path) -> None:
        if not path.exists():
            raise ValueError(f"Gene annotation BED not found: {path}")
        if not path.is_file():
            raise ValueError(f"Gene annotation BED must be a file: {path}")
        valid_rows = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 4:
                    raise ValueError(
                        f"Gene annotation BED must have at least 4 tab-separated columns: {path}"
                    )
                try:
                    int(parts[1])
                    int(parts[2])
                except ValueError as exc:
                    raise ValueError(f"Gene annotation BED start/end columns must be integers: {path}") from exc
                if not parts[3].strip():
                    raise ValueError(f"Gene annotation BED column 4 must contain gene IDs: {path}")
                valid_rows += 1
                if valid_rows >= 3:
                    break
        if valid_rows == 0:
            raise ValueError(f"Gene annotation BED does not contain any valid data rows: {path}")
