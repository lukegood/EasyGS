"""Protein function annotation tool using user-managed maize annotation resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path


@dataclass
class PreparedProteinFunctionAnnotationRun:
    """Prepared execution plan for protein function annotation."""

    launcher: str
    annotation_source: str
    command: list[str]
    genelist_txt_path: Path
    longest_cds_txt_path: Path
    proteins_tsv_path: Path
    output_dir: Path
    output_prefix: str
    gene_protein_map_path: Path
    protlist_path: Path
    protlist_stranno_path: Path
    annotation_tsv_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "annotation_source": self.annotation_source,
            "genelist_txt_path": str(self.genelist_txt_path),
            "longest_cds_txt_path": str(self.longest_cds_txt_path),
            "proteins_tsv_path": str(self.proteins_tsv_path),
            "output_dir": str(self.output_dir),
            "output_prefix": self.output_prefix,
            "gene_protein_map_path": str(self.gene_protein_map_path),
            "protlist_path": str(self.protlist_path),
            "protlist_stranno_path": str(self.protlist_stranno_path),
            "annotation_tsv_path": str(self.annotation_tsv_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunProteinFunctionAnnotationTool(PlinkToolBase, Tool):
    """Run maize protein function annotation for a gene list without enrichment."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="protein_function_annotation_analysis",
            default_output_subdir="protein_function_annotation",
            env_name="EasyGS_2",
        )
        self.script_path = self.skill_dir / "protein_function_annotation.sh"
        self.summary_script_path = self.skill_dir / "summarize_protein_function_annotation.py"
        self.resource_dir = resolve_user_resource_path("pfam_enrichment_analysis")
        self.longest_cds_txt_path = self.resource_dir / "all_maize_longest_cds.txt"
        self.proteins_tsv_path = self.resource_dir / "all_maize_genes_proteins.fa.tsv"

    @property
    def name(self) -> str:
        return "run_protein_function_annotation"

    @property
    def description(self) -> str:
        return (
            "Map maize genes to proteins using the user-managed longest-CDS resource, extract "
            "matching protein function/domain annotation rows from the maize proteins TSV resource "
            "in EasyGS_2, and export annotation tables without running enrichment."
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
                "annotation_source": {
                    "type": "string",
                    "description": (
                        "Optional annotation source/library name from the maize proteins TSV column 4. "
                        "Default: all. Use Pfam to return only PFAM rows. If you want to override it, "
                        "please provide it explicitly."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Default: "
                        "workspace/default_results/protein_function_annotation/. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional output prefix for annotation TSV and summary files. Default: "
                        "protein_function_annotation. If you want to override it, please provide it explicitly."
                    ),
                },
            },
            "required": ["genelist_txt"],
        }

    async def execute(
        self,
        genelist_txt: str,
        annotation_source: str | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                genelist_txt=genelist_txt,
                annotation_source=annotation_source,
                output_dir=output_dir,
                output_prefix=output_prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Protein function annotation failed.\n"
                f"- Gene list TXT: {prepared.genelist_txt_path}\n"
                f"- Maize longest CDS resource: {prepared.longest_cds_txt_path}\n"
                f"- Maize proteins TSV resource: {prepared.proteins_tsv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Protein function annotation completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Gene list TXT: {prepared.genelist_txt_path}",
            f"- Maize longest CDS resource: {prepared.longest_cds_txt_path}",
            f"- Maize proteins TSV resource: {prepared.proteins_tsv_path}",
            f"- Annotation source: {prepared.annotation_source}",
            f"- Output dir: {prepared.output_dir}",
            f"- Gene-protein map TSV: {prepared.gene_protein_map_path}",
            f"- protlist.txt: {prepared.protlist_path}",
            f"- protlist.stranno.tsv: {prepared.protlist_stranno_path}",
            f"- Protein function annotation TSV: {prepared.annotation_tsv_path}",
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
        annotation_source: str | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
    ) -> PreparedProteinFunctionAnnotationRun:
        genelist_txt_path = self._resolve_text_file(genelist_txt, "Gene list TXT")
        longest_cds_txt_path = self._resolve_longest_cds_resource()
        proteins_tsv_path = self._resolve_proteins_tsv_resource()

        self._validate_non_empty_lines(genelist_txt_path, "Gene list TXT")
        self._validate_maize_gene_ids(genelist_txt_path)
        self._validate_tabular_preview(longest_cds_txt_path, min_columns=2, label="Longest CDS TXT")
        self._validate_tabular_preview(proteins_tsv_path, min_columns=5, label="Protein annotation TSV")

        output_root = self._resolve_output_dir(output_dir)
        output_prefix_value = self._normalize_prefix_name(output_prefix, "protein_function_annotation")
        annotation_source_value = (annotation_source or "all").strip() or "all"

        gene_protein_map_path = output_root / "gene_protein_map.tsv"
        protlist_path = output_root / "protlist.txt"
        protlist_stranno_path = output_root / "protlist.stranno.tsv"
        annotation_tsv_path = output_root / f"{output_prefix_value}.tsv"
        summary_path = output_root / f"{output_prefix_value}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["awk", "python3"])
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
            "--gene-protein-map-output",
            str(gene_protein_map_path),
            "--protlist-output",
            str(protlist_path),
            "--protlist-stranno-output",
            str(protlist_stranno_path),
            "--annotation-tsv-output",
            str(annotation_tsv_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedProteinFunctionAnnotationRun(
            launcher=env_status["launcher"],
            annotation_source=annotation_source_value,
            command=command,
            genelist_txt_path=genelist_txt_path,
            longest_cds_txt_path=longest_cds_txt_path,
            proteins_tsv_path=proteins_tsv_path,
            output_dir=output_root,
            output_prefix=output_prefix_value,
            gene_protein_map_path=gene_protein_map_path,
            protlist_path=protlist_path,
            protlist_stranno_path=protlist_stranno_path,
            annotation_tsv_path=annotation_tsv_path,
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
                "Missing required resource for protein_function_annotation_analysis:\n"
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
                "Missing required resource for protein_function_annotation_analysis:\n"
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
                "This protein function annotation tool supports maize only. "
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
