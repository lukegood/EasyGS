"""PFAM/domain enrichment tool using user-managed maize annotation resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path


@dataclass
class PreparedPfamEnrichmentRun:
    """Prepared execution plan for PFAM/domain enrichment."""

    launcher: str
    annotation_source: str
    min_count_in_candidates: int
    p_adjust_method: str
    fdr_cutoff: float
    command: list[str]
    genelist_txt_path: Path
    longest_cds_txt_path: Path
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
            "annotation_source": self.annotation_source,
            "min_count_in_candidates": self.min_count_in_candidates,
            "p_adjust_method": self.p_adjust_method,
            "fdr_cutoff": self.fdr_cutoff,
            "genelist_txt_path": str(self.genelist_txt_path),
            "longest_cds_txt_path": str(self.longest_cds_txt_path),
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
    """Run maize candidate-protein extraction and PFAM/domain enrichment."""

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
        self.r_script_path = self.skill_dir / "run_pfam_enrichment.R"
        self.summary_script_path = self.skill_dir / "summarize_pfam_enrichment.py"
        self.resource_dir = resolve_user_resource_path("pfam_enrichment_analysis")
        self.longest_cds_txt_path = self.resource_dir / "all_maize_longest_cds.txt"
        self.proteins_tsv_path = self.resource_dir / "all_maize_genes_proteins.fa.tsv"

    @property
    def name(self) -> str:
        return "run_pfam_enrichment"

    @property
    def description(self) -> str:
        return (
            "Run protein-list extraction from a gene list using maize longest-CDS mapping "
            "and maize protein-annotation TSV resources from "
            "~/.easygs/resources/pfam_enrichment_analysis/, then perform PFAM/domain enrichment "
            "in EasyGS_2. "
            "This tool supports maize data only."
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
                "background_protein_txt": {
                    "type": "string",
                    "description": (
                        "Optional custom background protein list TXT, one protein ID per line. "
                        "Default: use all annotated proteins from the selected annotation source. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "annotation_source": {
                    "type": "string",
                    "description": (
                        "Annotation source/library name used for enrichment from the maize proteins TSV "
                        "column 4. Default: Pfam. If you want to override it, please provide it explicitly."
                    ),
                },
                "min_count_in_candidates": {
                    "type": "integer",
                    "minimum": 1,
                    "description": (
                        "Minimum candidate count required for significant-domain reporting. "
                        "Default: 5. If you want to override it, please provide it explicitly."
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
                        "Optional output prefix for enrichment CSV files. Default: pfam_enrichment. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
            },
            "required": ["genelist_txt"],
        }

    async def execute(
        self,
        genelist_txt: str,
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
                f"- Gene list TXT: {prepared.genelist_txt_path}\n"
                f"- Maize longest CDS resource: {prepared.longest_cds_txt_path}\n"
                f"- Maize proteins TSV resource: {prepared.proteins_tsv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "PFAM/domain enrichment completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Gene list TXT: {prepared.genelist_txt_path}",
            f"- Maize longest CDS resource: {prepared.longest_cds_txt_path}",
            f"- Maize proteins TSV resource: {prepared.proteins_tsv_path}",
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
        background_protein_txt: str | None = None,
        annotation_source: str | None = None,
        min_count_in_candidates: int | None = None,
        p_adjust_method: str | None = None,
        fdr_cutoff: float | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
    ) -> PreparedPfamEnrichmentRun:
        genelist_txt_path = self._resolve_text_file(genelist_txt, "Gene list TXT")
        longest_cds_txt_path = self._resolve_longest_cds_resource()
        proteins_tsv_path = self._resolve_proteins_tsv_resource()
        background_protein_txt_path = (
            self._resolve_text_file(background_protein_txt, "Background protein TXT")
            if background_protein_txt
            else None
        )

        self._validate_non_empty_lines(genelist_txt_path, "Gene list TXT")
        self._validate_maize_gene_ids(genelist_txt_path)
        self._validate_tabular_preview(longest_cds_txt_path, min_columns=2, label="Longest CDS TXT")
        self._validate_tabular_preview(proteins_tsv_path, min_columns=5, label="Protein annotation TSV")

        output_root = self._resolve_output_dir(output_dir)
        output_prefix_value = self._normalize_prefix_name(output_prefix, "pfam_enrichment")
        annotation_source_value = (annotation_source or "Pfam").strip() or "Pfam"
        min_count_value = int(min_count_in_candidates if min_count_in_candidates is not None else 5)
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
            "--longest-cds-txt",
            str(longest_cds_txt_path),
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
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if background_protein_txt_path is not None:
            command.extend(["--background-protein-txt", str(background_protein_txt_path)])

        return PreparedPfamEnrichmentRun(
            launcher=env_status["launcher"],
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

    def _resolve_proteins_tsv_resource(self) -> Path:
        path = self.proteins_tsv_path
        if not path.exists():
            raise ValueError(
                "Missing required resource for pfam_enrichment_analysis:\n"
                f"{path}\n\n"
                "Please download or prepare all_maize_genes_proteins.fa.tsv and place it at "
                "the path above. Set EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if not path.is_file():
            raise ValueError(f"Maize proteins TSV resource must be a file: {path}")
        if path.suffix.lower() != ".tsv":
            raise ValueError(f"Maize proteins TSV resource must end with .tsv: {path}")
        return path

    def _validate_non_empty_lines(self, path: Path, label: str) -> None:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        if not lines:
            raise ValueError(f"{label} is empty: {path}")

    def _validate_maize_gene_ids(self, path: Path) -> None:
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        invalid = [value for value in lines if not value.startswith("Zm")]
        if invalid:
            preview = ", ".join(invalid[:3])
            raise ValueError(
                "This PFAM/domain enrichment tool supports maize only. "
                f"Found non-maize gene IDs: {preview}"
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
