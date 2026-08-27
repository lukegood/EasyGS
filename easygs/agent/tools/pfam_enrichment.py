"""PFAM/domain enrichment using species-specific user-managed resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path

_SPECIES_ANNOTATION_FILENAMES = {
    "maize": "all_maize_genes_proteins.fa.tsv",
    "wheat": "wheat_interpro.tsv",
    "rice": "Osativa_323_v7.0.protein_primaryTranscriptOnly.fa.tsv",
}


@dataclass
class PreparedPfamEnrichmentRun:
    """Prepared execution plan for PFAM/domain enrichment."""

    launcher: str
    species: str
    annotation_source: str
    min_count_in_candidates: int
    p_adjust_method: str
    fdr_cutoff: float
    command: list[str]
    genelist_txt_path: Path
    longest_cds_txt_path: Path | None
    proteins_tsv_path: Path
    background_protein_txt_path: Path | None
    output_dir: Path
    output_prefix: str
    protlist_path: Path
    protlist_stranno_path: Path
    source_annotation_tsv_path: Path
    all_enrichment_csv_path: Path
    sig_enrichment_csv_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "species": self.species,
            "annotation_source": self.annotation_source,
            "min_count_in_candidates": self.min_count_in_candidates,
            "p_adjust_method": self.p_adjust_method,
            "fdr_cutoff": self.fdr_cutoff,
            "genelist_txt_path": str(self.genelist_txt_path),
            "longest_cds_txt_path": (
                str(self.longest_cds_txt_path) if self.longest_cds_txt_path else ""
            ),
            "proteins_tsv_path": str(self.proteins_tsv_path),
            "background_protein_txt_path": (
                str(self.background_protein_txt_path) if self.background_protein_txt_path else ""
            ),
            "output_dir": str(self.output_dir),
            "output_prefix": self.output_prefix,
            "protlist_path": str(self.protlist_path),
            "protlist_stranno_path": str(self.protlist_stranno_path),
            "source_annotation_tsv_path": str(self.source_annotation_tsv_path),
            "all_enrichment_csv_path": str(self.all_enrichment_csv_path),
            "sig_enrichment_csv_path": str(self.sig_enrichment_csv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunPfamEnrichmentTool(PlinkToolBase, Tool):
    """Run maize, wheat, or rice PFAM/domain enrichment."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="pfam_enrichment_analysis",
            default_output_subdir="pfam_enrichment",
            env_name="EasyGS_2",
        )
        self.script_path = self.skill_dir / "pfam_enrichment.sh"
        self.preprocess_script_path = self.skill_dir / "prepare_pfam_annotations.py"
        self.r_script_path = self.skill_dir / "run_pfam_enrichment.R"
        self.summary_script_path = self.skill_dir / "summarize_pfam_enrichment.py"
        self.resource_dir = resolve_user_resource_path("pfam_enrichment_analysis")
        self.longest_cds_txt_path = self.resource_dir / "all_maize_longest_cds.txt"
        self.proteins_tsv_path = self.resource_dir / "all_maize_genes_proteins.fa.tsv"
        self.annotation_resource_paths = {
            species: self.resource_dir / filename
            for species, filename in _SPECIES_ANNOTATION_FILENAMES.items()
        }

    @property
    def name(self) -> str:
        return "run_pfam_enrichment"

    @property
    def description(self) -> str:
        return (
            "Run PFAM/domain enrichment for maize, wheat, or rice in EasyGS_2. Species-specific "
            "annotation resources are selected automatically; large wheat/rice InterProScan "
            "files are processed as streams."
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
                        "rice:\nLOC_Os02g07880\nLOC_Os01g19750\nLOC_Os05g33910\nLOC_Os07g42632"
                    ),
                },
                "species": {
                    "type": "string",
                    "enum": ["maize", "wheat", "rice"],
                    "default": "maize",
                    "description": (
                        "Species for the input genes: maize, wheat, or rice. Default: maize. "
                        "The matching annotation resources are selected automatically."
                    ),
                },
                "background_protein_txt": {
                    "type": "string",
                    "description": (
                        "Optional custom background ID list TXT, one gene/protein ID per line. "
                        "Default: all IDs annotated by the selected source. Numeric transcript "
                        "suffixes are normalized for wheat and rice. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "annotation_source": {
                    "type": "string",
                    "description": (
                        "Annotation source/library name used for enrichment from annotation column 4. "
                        "Default: Pfam. If you want to override it, please provide it explicitly."
                    ),
                },
                "min_count_in_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "description": (
                        "Minimum candidate count required for significant-domain reporting. "
                        "Default: 5 for maize and 2 for wheat/rice."
                    ),
                },
                "p_adjust_method": {
                    "type": "string",
                    "description": (
                        "P-value adjustment method passed to p.adjust. Default: BH. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "fdr_cutoff": {
                    "type": "number",
                    "description": (
                        "Adjusted p-value cutoff for significant domains. Default: 0.05. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Default: workspace/default_results/pfam_enrichment/. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional output prefix. Default: pfam_enrichment for maize and "
                        "<species>_pfam_enrichment for wheat/rice. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
            },
            "required": ["genelist_txt"],
        }

    async def execute(
        self,
        genelist_txt: str,
        species: str = "maize",
        background_protein_txt: str | None = None,
        annotation_source: str | None = None,
        min_count_in_candidates: int | None = None,
        p_adjust_method: str | None = None,
        fdr_cutoff: float | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                genelist_txt=genelist_txt,
                species=species,
                background_protein_txt=background_protein_txt,
                annotation_source=annotation_source,
                min_count_in_candidates=min_count_in_candidates,
                p_adjust_method=p_adjust_method,
                fdr_cutoff=fdr_cutoff,
                output_dir=output_dir,
                output_prefix=output_prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: PFAM/domain enrichment failed.\n"
                f"- Species: {prepared.species}\n"
                f"- Gene list TXT: {prepared.genelist_txt_path}\n"
                f"- Longest CDS resource: {prepared.longest_cds_txt_path or 'not required'}\n"
                f"- Annotation TSV resource: {prepared.proteins_tsv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "PFAM/domain enrichment completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Species: {prepared.species}",
            f"- Gene list TXT: {prepared.genelist_txt_path}",
            f"- Longest CDS resource: {prepared.longest_cds_txt_path or 'not required'}",
            f"- Annotation TSV resource: {prepared.proteins_tsv_path}",
            f"- Background protein TXT: {prepared.background_protein_txt_path or 'default(all annotated proteins)'}",
            f"- Annotation source: {prepared.annotation_source}",
            f"- Min candidate count: {prepared.min_count_in_candidates}",
            f"- P adjust method: {prepared.p_adjust_method}",
            f"- FDR cutoff: {prepared.fdr_cutoff}",
            f"- Output dir: {prepared.output_dir}",
            f"- protlist.txt: {prepared.protlist_path}",
            f"- protlist.stranno.tsv: {prepared.protlist_stranno_path}",
            f"- Source-filtered TSV: {prepared.source_annotation_tsv_path}",
            f"- All enrichment CSV: {prepared.all_enrichment_csv_path}",
            f"- Significant enrichment CSV: {prepared.sig_enrichment_csv_path}",
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
        background_protein_txt: str | None = None,
        annotation_source: str | None = None,
        min_count_in_candidates: int | None = None,
        p_adjust_method: str | None = None,
        fdr_cutoff: float | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
    ) -> PreparedPfamEnrichmentRun:
        species_value = self._normalize_species(species)
        genelist_txt_path = self._resolve_text_file(genelist_txt, "Gene list TXT")
        longest_cds_txt_path = (
            self._resolve_longest_cds_resource() if species_value == "maize" else None
        )
        proteins_tsv_path = self._resolve_annotation_resource(species_value)
        background_protein_txt_path = (
            self._resolve_text_file(background_protein_txt, "Background protein TXT")
            if background_protein_txt
            else None
        )

        self._validate_non_empty_lines(genelist_txt_path, "Gene list TXT")
        self._validate_gene_ids(genelist_txt_path, species_value)
        if longest_cds_txt_path is not None:
            self._validate_tabular_preview(
                longest_cds_txt_path, min_columns=2, label="Longest CDS TXT"
            )
        self._validate_tabular_preview(proteins_tsv_path, min_columns=5, label="Protein annotation TSV")

        output_root = self._resolve_output_dir(output_dir)
        default_prefix = (
            "pfam_enrichment" if species_value == "maize" else f"{species_value}_pfam_enrichment"
        )
        output_prefix_value = self._normalize_prefix_name(output_prefix, default_prefix)
        annotation_source_value = (annotation_source or "Pfam").strip() or "Pfam"
        default_min_count = 5 if species_value == "maize" else 2
        min_count_value = int(
            min_count_in_candidates
            if min_count_in_candidates is not None
            else default_min_count
        )
        if min_count_value < 1:
            raise ValueError("min_count_in_candidates must be >= 1")
        p_adjust_method_value = (p_adjust_method or "BH").strip() or "BH"
        fdr_cutoff_value = float(fdr_cutoff if fdr_cutoff is not None else 0.05)
        if fdr_cutoff_value < 0 or fdr_cutoff_value > 1:
            raise ValueError("fdr_cutoff must be between 0 and 1")

        protlist_path = output_root / "protlist.txt"
        protlist_stranno_path = output_root / "protlist.stranno.tsv"
        source_annotation_tsv_path = output_root / (
            f"{output_prefix_value}_{annotation_source_value}.source.tsv"
        )
        all_enrichment_csv_path = output_root / f"{output_prefix_value}_all_pfam_enrichment.csv"
        sig_enrichment_csv_path = output_root / f"{output_prefix_value}_sig_pfam.csv"
        summary_path = output_root / f"{output_prefix_value}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "preprocessing script": self.preprocess_script_path,
            "R script": self.r_script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["Rscript", "awk", "python3"])
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
            "--proteins-tsv",
            str(proteins_tsv_path),
            "--annotation-source",
            annotation_source_value,
            "--min-count-in-candidates",
            str(min_count_value),
            "--p-adjust-method",
            p_adjust_method_value,
            "--fdr-cutoff",
            str(fdr_cutoff_value),
            "--protlist-output",
            str(protlist_path),
            "--protlist-stranno-output",
            str(protlist_stranno_path),
            "--source-annotation-tsv-output",
            str(source_annotation_tsv_path),
            "--all-enrichment-csv-output",
            str(all_enrichment_csv_path),
            "--sig-enrichment-csv-output",
            str(sig_enrichment_csv_path),
            "--summary-output",
            str(summary_path),
            "--preprocess-script",
            str(self.preprocess_script_path),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if longest_cds_txt_path is not None:
            command.extend(["--longest-cds-txt", str(longest_cds_txt_path)])
        if background_protein_txt_path is not None:
            command.extend(["--background-protein-txt", str(background_protein_txt_path)])

        return PreparedPfamEnrichmentRun(
            launcher=env_status["launcher"],
            species=species_value,
            annotation_source=annotation_source_value,
            min_count_in_candidates=min_count_value,
            p_adjust_method=p_adjust_method_value,
            fdr_cutoff=fdr_cutoff_value,
            command=command,
            genelist_txt_path=genelist_txt_path,
            longest_cds_txt_path=longest_cds_txt_path,
            proteins_tsv_path=proteins_tsv_path,
            background_protein_txt_path=background_protein_txt_path,
            output_dir=output_root,
            output_prefix=output_prefix_value,
            protlist_path=protlist_path,
            protlist_stranno_path=protlist_stranno_path,
            source_annotation_tsv_path=source_annotation_tsv_path,
            all_enrichment_csv_path=all_enrichment_csv_path,
            sig_enrichment_csv_path=sig_enrichment_csv_path,
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

    def _resolve_longest_cds_resource(self) -> Path:
        path = self.longest_cds_txt_path
        if not path.exists():
            raise ValueError(
                "Missing required resource for pfam_enrichment_analysis:\n"
                f"{path}\n\n"
                "Please download or prepare all_maize_longest_cds.txt and place it at the "
                "path above. Set EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if not path.is_file():
            raise ValueError(f"Maize longest CDS resource must be a file: {path}")
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Maize longest CDS resource must end with .txt: {path}")
        return path

    def _normalize_species(self, value: str) -> str:
        species = str(value).strip().lower()
        if species not in _SPECIES_ANNOTATION_FILENAMES:
            allowed = ", ".join(_SPECIES_ANNOTATION_FILENAMES)
            raise ValueError(f"species must be one of: {allowed}")
        return species

    def _resolve_annotation_resource(self, species: str) -> Path:
        path = self.annotation_resource_paths[species]
        filename = _SPECIES_ANNOTATION_FILENAMES[species]
        if not path.exists():
            raise ValueError(
                "Missing required resource for pfam_enrichment_analysis:\n"
                f"{path}\n\n"
                f"Please download or prepare {filename} and place it at "
                "the path above. Set EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if not path.is_file():
            raise ValueError(f"Protein annotation TSV resource must be a file: {path}")
        if path.suffix.lower() != ".tsv":
            raise ValueError(f"Protein annotation resource must end with .tsv: {path}")
        return path

    def _validate_non_empty_lines(self, path: Path, label: str) -> None:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        if not lines:
            raise ValueError(f"{label} is empty: {path}")

    def _validate_gene_ids(self, path: Path, species: str) -> None:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        prefixes = {
            "maize": ("Zm", "GRMZM"),
            "wheat": ("TraesCS",),
            "rice": ("LOC_Os", "ChrSy"),
        }
        invalid = [value for value in lines if not value.startswith(prefixes[species])]
        if invalid:
            preview = ", ".join(invalid[:3])
            raise ValueError(
                f"Gene IDs do not look like {species} IDs: {preview}"
            )

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
