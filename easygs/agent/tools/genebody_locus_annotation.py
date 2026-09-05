"""Genebody locus annotation for maize, wheat, and rice loci."""

from __future__ import annotations

import re
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
class PreparedGenebodyLocusAnnotationRun:
    """Prepared execution plan for genebody locus annotation."""

    launcher: str
    species: str
    command: list[str]
    locus_list_path: Path
    gene_bed_path: Path
    output_dir: Path
    site_gene_path: Path
    gene_list_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "species": self.species,
            "locus_list_path": str(self.locus_list_path),
            "gene_bed_path": str(self.gene_bed_path),
            "output_dir": str(self.output_dir),
            "site_gene_path": str(self.site_gene_path),
            "gene_list_path": str(self.gene_list_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }


class RunGenebodyLocusAnnotationTool(PlinkToolBase, Tool):
    """Annotate loci that fall inside maize, wheat, or rice gene bodies."""

    _LOCUS_RE = re.compile(r"^(?P<chromosome>[A-Za-z0-9_]+)[.]s_(?P<position>[0-9]+)$")

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="genebody_locus_annotation_analysis",
            default_output_subdir="genebody_locus_annotation",
            env_name="EasyGS_2",
        )
        self.script_path = self.skill_dir / "genebody_locus_annotation.sh"
        self.summary_script_path = self.skill_dir / "summarize_genebody_locus_annotation.py"
        self.gene_bed_resource_paths = {
            species: resolve_user_resource_path("genebody_locus_annotation_analysis", filename)
            for species, filename in _SPECIES_GENE_BED_FILENAMES.items()
        }

    @property
    def name(self) -> str:
        return "run_genebody_locus_annotation"

    @property
    def description(self) -> str:
        return (
            "Annotate loci that fall in maize, wheat, or rice gene bodies from a TXT locus "
            "list. The matching gene-BED resource is selected automatically, and the tool "
            "exports locus-to-gene pairs and the gene list."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "locus_list": {
                    "type": "string",
                    "description": (
                        "User-provided TXT file with one locus ID per line in chr<chrom>.s_<position> "
                        "format. Example:\n"
                        "chr1.s_27738\n"
                        "chr1.s_201492\n"
                        "chr1.s_251434\n"
                        "chr1.s_294503\n"
                        "chr1.s_323280"
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
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Defaults to "
                        "workspace/default_results/genebody_locus_annotation/."
                    ),
                },
            },
            "required": ["locus_list"],
        }

    async def execute(
        self,
        locus_list: str,
        species: str = "maize",
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        if kwargs.get("gene_bed"):
            return (
                "Error: gene_bed is not a public parameter for "
                "genebody_locus_annotation_analysis. Select species=maize, wheat, or rice; "
                "EasyGS will use the matching resource."
            )
        try:
            prepared = await self.prepare_run(
                locus_list=locus_list,
                species=species,
                output_dir=output_dir,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Genebody locus annotation failed.\n"
                f"- Species: {prepared.species}\n"
                f"- Locus list: {prepared.locus_list_path}\n"
                f"- Gene BED resource: {prepared.gene_bed_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Genebody locus annotation completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Species: {prepared.species}",
            f"- Locus list: {prepared.locus_list_path}",
            f"- Gene BED resource: {prepared.gene_bed_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Site-gene output: {prepared.site_gene_path}",
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
        locus_list: str,
        species: str = "maize",
        output_dir: str | None = None,
    ) -> PreparedGenebodyLocusAnnotationRun:
        species_value = self._normalize_species(species)
        locus_list_path = self._resolve_locus_list(locus_list)
        locus_chromosomes = self._validate_locus_list(locus_list_path)
        gene_bed_path = self._resolve_gene_bed_resource(species_value)
        gene_bed_chromosomes = self._validate_gene_bed(gene_bed_path)
        self._validate_chromosome_match(
            locus_chromosomes,
            gene_bed_chromosomes,
            gene_bed_path,
        )
        output_root = self._resolve_output_dir(output_dir)

        site_gene_path = output_root / "位于genebody的位点及其对应的基因.txt"
        gene_list_path = output_root / "位于genebody的基因.txt"
        summary_path = output_root / "genebody_locus_annotation_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")
            if not path.is_file():
                raise ValueError(f"{label} must be a file: {path}")

        env_status = await self._get_environment_status(["bedtools", "python3", "awk", "cut"])
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
            "--locus-list",
            str(locus_list_path),
            "--species",
            species_value,
            "--site-gene-output",
            str(site_gene_path),
            "--gene-output",
            str(gene_list_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--gene-bed",
            str(gene_bed_path),
        ]

        return PreparedGenebodyLocusAnnotationRun(
            launcher=env_status["launcher"],
            species=species_value,
            command=command,
            locus_list_path=locus_list_path,
            gene_bed_path=gene_bed_path,
            output_dir=output_root,
            site_gene_path=site_gene_path,
            gene_list_path=gene_list_path,
            summary_path=summary_path,
        )

    def _resolve_locus_list(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"Locus list not found: {path}")
        if not path.is_file():
            raise ValueError(f"Locus list must be a file: {path}")
        return path

    def _normalize_species(self, value: str) -> str:
        species = str(value).strip().lower()
        if species not in _SPECIES_GENE_BED_FILENAMES:
            allowed = ", ".join(_SPECIES_GENE_BED_FILENAMES)
            raise ValueError(f"species must be one of: {allowed}")
        return species

    @staticmethod
    def _canonical_chromosome(value: str) -> str:
        chromosome = value.strip()
        if chromosome.lower().startswith("chr"):
            chromosome = chromosome[3:]
        return chromosome

    def _resolve_gene_bed_resource(self, species: str) -> Path:
        filename = _SPECIES_GENE_BED_FILENAMES[species]
        path = self.gene_bed_resource_paths[species]
        if not path.exists():
            raise ValueError(
                "Missing required resource for genebody_locus_annotation_analysis:\n"
                f"{path}\n\n"
                f"Please prepare {filename} and place it at the path above. Set "
                "EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if path.is_symlink():
            raise ValueError(f"Gene BED resource must be a real file, not a symbolic link: {path}")
        if not path.is_file():
            raise ValueError(f"Gene BED resource must be a file: {path}")
        return path

    def _validate_locus_list(self, path: Path) -> set[str]:
        valid_rows = 0
        chromosomes: set[str] = set()
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                fields = line.split()
                if len(fields) != 1:
                    raise ValueError(
                        "Locus list must contain exactly one locus ID per non-empty line "
                        f"(line {line_number} in {path}: {line})"
                    )
                locus = fields[0]
                match = self._LOCUS_RE.fullmatch(locus)
                if match is None:
                    raise ValueError(
                        "Locus list rows must look like chr1.s_201492, Chr1.s_201492, "
                        "or Chr1A.s_201492 "
                        f"(line {line_number} in {path}: {line})"
                    )
                chromosomes.add(self._canonical_chromosome(match.group("chromosome")))
                valid_rows += 1
        if valid_rows == 0:
            raise ValueError(f"Locus list does not contain any valid locus rows: {path}")
        return chromosomes

    def _validate_gene_bed(self, path: Path) -> set[str]:
        valid_rows = 0
        chromosomes: set[str] = set()
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 4:
                    raise ValueError(
                        "Gene BED resource must have at least four tab-separated columns "
                        f"(line {line_number} in {path})"
                    )
                chromosome = parts[0].strip()
                try:
                    start = int(parts[1])
                    end = int(parts[2])
                except ValueError as exc:
                    raise ValueError(
                        f"Gene BED start/end must be integers (line {line_number} in {path})"
                    ) from exc
                if not chromosome or start < 0 or end <= start or not parts[3].strip():
                    raise ValueError(
                        "Gene BED rows require a chromosome, 0 <= start < end, and gene ID "
                        f"(line {line_number} in {path})"
                    )
                chromosomes.add(self._canonical_chromosome(chromosome))
                valid_rows += 1
        if valid_rows == 0:
            raise ValueError(f"Gene BED resource does not contain any valid rows: {path}")
        return chromosomes

    def _validate_chromosome_match(
        self,
        locus_chromosomes: set[str],
        gene_bed_chromosomes: set[str],
        gene_bed_path: Path,
    ) -> None:
        missing = locus_chromosomes - gene_bed_chromosomes
        if not missing:
            return
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            "Locus chromosome names do not match the selected species gene BED after "
            f"normalization. Missing from gene BED: {missing_text}. Gene BED: {gene_bed_path}"
        )
