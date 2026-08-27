"""Candidate gene extraction based on LD-window expansion and gene BED resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path

_SPECIES_GENE_BED_FILENAMES = {
    "maize": "allV4gene.bed",
    "wheat": "allwheatgene.bed",
    "rice": "allricegene.bed",
}


@dataclass
class PreparedCandidateGeneExtractionRun:
    """Prepared execution plan for candidate gene extraction."""

    launcher: str
    species: str
    ld_distance: int
    command: list[str]
    bed_path: Path
    gene_bed_path: Path
    output_dir: Path
    output_prefix: str
    extended_bed_path: Path
    gene_list_path: Path
    detailed_tsv_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "species": self.species,
            "ld_distance": self.ld_distance,
            "bed_path": str(self.bed_path),
            "gene_bed_path": str(self.gene_bed_path),
            "output_dir": str(self.output_dir),
            "output_prefix": self.output_prefix,
            "extended_bed_path": str(self.extended_bed_path),
            "gene_list_path": str(self.gene_list_path),
            "detailed_tsv_path": str(self.detailed_tsv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }


class RunCandidateGeneExtractionTool(PlinkToolBase, Tool):
    """Extract candidate genes around loci for maize, wheat, or rice."""

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
        self.gene_bed_resource_paths = {
            species: resolve_user_resource_path("candidate_gene_extraction_analysis", filename)
            for species, filename in _SPECIES_GENE_BED_FILENAMES.items()
        }

    @property
    def name(self) -> str:
        return "run_candidate_gene_extraction"

    @property
    def description(self) -> str:
        return (
            "Run candidate-gene extraction for maize, wheat, or rice in EasyGS_2 by expanding "
            "a user BED with an LD distance and intersecting it with the automatically selected "
            "species gene-BED resource."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bed": {
                    "type": "string",
                    "description": (
                        "User-provided BED file containing loci to expand. Wheat example:\n"
                        "Chr1A\t207606062\t207606063\n"
                        "Chr3A\t180017154\t180017155\n"
                        "Chr4B\t191156851\t191156852"
                    ),
                },
                "species": {
                    "type": "string",
                    "enum": ["maize", "wheat", "rice"],
                    "default": "maize",
                    "description": (
                        "Species for the input loci: maize, wheat, or rice. Default: maize. "
                        "The matching gene BED is selected automatically from EasyGS resources."
                    ),
                },
                "ld_distance": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Optional LD expansion distance in bp. Default: 50000. Use 100000 to "
                        "reproduce the wheat/rice examples."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Defaults to "
                        "workspace/default_results/candidate_gene_extraction/."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional filename prefix for all outputs. Defaults to the input BED "
                        "stem; for example testwheat produces testwheat.extend.bed, "
                        "testwheat.txt, and testwheat.detailed.tsv."
                    ),
                },
            },
            "required": ["bed"],
        }

    async def execute(
        self,
        bed: str,
        species: str = "maize",
        ld_distance: int | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        if kwargs.get("gene_bed"):
            return (
                "Error: gene_bed is no longer a public parameter for "
                "candidate_gene_extraction_analysis. Select species=maize, wheat, or rice; "
                "EasyGS will use the matching resource."
            )
        try:
            prepared = await self.prepare_run(
                bed=bed,
                species=species,
                ld_distance=ld_distance,
                output_dir=output_dir,
                output_prefix=output_prefix,
            )
        except (PermissionError, ValueError) as exc:
            return f"Error: {exc}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Candidate gene extraction failed.\n"
                f"- Species: {prepared.species}\n"
                f"- BED: {prepared.bed_path}\n"
                f"- Gene BED resource: {prepared.gene_bed_path}\n"
                f"- LD distance: {prepared.ld_distance}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Candidate gene extraction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Species: {prepared.species}",
            f"- BED: {prepared.bed_path}",
            f"- Gene BED resource: {prepared.gene_bed_path}",
            f"- LD distance: {prepared.ld_distance}bp",
            f"- Output dir: {prepared.output_dir}",
            f"- Extended BED: {prepared.extended_bed_path}",
            f"- Gene list: {prepared.gene_list_path}",
            f"- Detailed matches: {prepared.detailed_tsv_path}",
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
        species: str = "maize",
        ld_distance: int | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
    ) -> PreparedCandidateGeneExtractionRun:
        species_value = self._normalize_species(species)
        bed_path = self._resolve_bed_file(bed)
        bed_chromosomes = self._validate_bed(bed_path)
        gene_bed_path = self._resolve_gene_bed_resource(species_value)
        gene_bed_chromosomes = self._validate_gene_bed(gene_bed_path)
        self._validate_chromosome_match(
            bed_chromosomes,
            gene_bed_chromosomes,
            gene_bed_path,
        )

        ld_distance_value = int(ld_distance if ld_distance is not None else 50000)
        if ld_distance_value < 0:
            raise ValueError("ld_distance must be >= 0")

        output_root = self._resolve_output_dir(output_dir)
        output_prefix_value = self._validate_output_prefix(output_prefix, bed_path)
        extended_bed_path = output_root / f"{output_prefix_value}.extend.bed"
        gene_list_path = output_root / f"{output_prefix_value}.txt"
        detailed_tsv_path = output_root / f"{output_prefix_value}.detailed.tsv"
        summary_path = output_root / f"{output_prefix_value}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["bedtools", "python3", "awk", "sort"])
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
            "--species",
            species_value,
            "--bed",
            str(bed_path),
            "--ld-distance",
            str(ld_distance_value),
            "--gene-bed",
            str(gene_bed_path),
            "--extended-bed-output",
            str(extended_bed_path),
            "--gene-list-output",
            str(gene_list_path),
            "--detailed-output",
            str(detailed_tsv_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedCandidateGeneExtractionRun(
            launcher=env_status["launcher"],
            species=species_value,
            ld_distance=ld_distance_value,
            command=command,
            bed_path=bed_path,
            gene_bed_path=gene_bed_path,
            output_dir=output_root,
            output_prefix=output_prefix_value,
            extended_bed_path=extended_bed_path,
            gene_list_path=gene_list_path,
            detailed_tsv_path=detailed_tsv_path,
            summary_path=summary_path,
        )

    def _normalize_species(self, value: str) -> str:
        species = str(value).strip().lower()
        if species not in _SPECIES_GENE_BED_FILENAMES:
            allowed = ", ".join(_SPECIES_GENE_BED_FILENAMES)
            raise ValueError(f"species must be one of: {allowed}")
        return species

    def _resolve_bed_file(self, value: str) -> Path:
        if not value:
            raise ValueError("BED input is required.")
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"BED file not found: {path}")
        if not path.is_file():
            raise ValueError(f"BED input must be a file: {path}")
        if path.suffix.lower() != ".bed":
            raise ValueError(f"BED input must end with .bed: {path}")
        return path

    def _resolve_gene_bed_resource(self, species: str) -> Path:
        filename = _SPECIES_GENE_BED_FILENAMES[species]
        path = self.gene_bed_resource_paths[species]
        if not path.exists():
            raise ValueError(
                "Missing required resource for candidate_gene_extraction_analysis:\n"
                f"{path}\n\n"
                f"Please prepare {filename} and place it at the path above. Set "
                "EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if not path.is_file():
            raise ValueError(f"Gene BED resource must be a file: {path}")
        return path

    def _validate_output_prefix(self, value: str | None, bed_path: Path) -> str:
        candidate = (value or bed_path.stem).strip() or bed_path.stem
        if candidate in {".", ".."} or Path(candidate).name != candidate or "\\" in candidate:
            raise ValueError("output_prefix must be a filename prefix without directory components")
        return candidate

    def _validate_bed(self, path: Path) -> set[str]:
        return self._validate_bed_rows(path, minimum_columns=3, label="BED input")

    def _validate_gene_bed(self, path: Path) -> set[str]:
        return self._validate_bed_rows(
            path,
            minimum_columns=4,
            label="Gene BED resource",
            require_gene_id=True,
        )

    def _validate_bed_rows(
        self,
        path: Path,
        *,
        minimum_columns: int,
        label: str,
        require_gene_id: bool = False,
    ) -> set[str]:
        valid_rows = 0
        chromosomes: set[str] = set()
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < minimum_columns:
                    raise ValueError(
                        f"{label} must have at least {minimum_columns} tab-separated columns: {path}"
                    )
                chromosome = parts[0].strip()
                if not chromosome:
                    raise ValueError(f"{label} chromosome column must not be empty: {path}")
                try:
                    start = int(parts[1])
                    end = int(parts[2])
                except ValueError as exc:
                    raise ValueError(f"{label} start/end columns must be integers: {path}") from exc
                if start < 0 or end <= start:
                    raise ValueError(
                        f"{label} coordinates must satisfy 0 <= start < end: {path}"
                    )
                if require_gene_id and not parts[3].strip():
                    raise ValueError(f"{label} column 4 must contain gene IDs: {path}")
                chromosomes.add(chromosome)
                valid_rows += 1
        if valid_rows == 0:
            raise ValueError(f"{label} does not contain any valid data rows: {path}")
        return chromosomes

    def _validate_chromosome_match(
        self,
        bed_chromosomes: set[str],
        gene_bed_chromosomes: set[str],
        gene_bed_path: Path,
    ) -> None:
        missing = bed_chromosomes - gene_bed_chromosomes
        if not missing:
            return
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            "BED chromosome names do not match the selected species gene BED. "
            f"Missing from gene BED: {missing_text}. Gene BED: {gene_bed_path}"
        )
