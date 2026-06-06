"""Gene function annotation/enrichment tool backed by clusterProfiler."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedGeneFunctionAnnotationRun:
    """Prepared execution plan for gene function annotation."""

    launcher: str
    gene_column: str
    entrez_column: str
    annotationhub_id: str
    kegg_organism: str
    go_ontology: str
    kegg_pvalue_threshold: float
    go_pvalue_threshold: float
    command: list[str]
    genelist_txt_path: Path
    entrez_map_csv_path: Path
    output_dir: Path
    kegg_txt_path: Path
    kegg_png_path: Path
    go_txt_path: Path
    go_png_path: Path
    mapping_summary_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "gene_column": self.gene_column,
            "entrez_column": self.entrez_column,
            "annotationhub_id": self.annotationhub_id,
            "kegg_organism": self.kegg_organism,
            "go_ontology": self.go_ontology,
            "kegg_pvalue_threshold": self.kegg_pvalue_threshold,
            "go_pvalue_threshold": self.go_pvalue_threshold,
            "genelist_txt_path": str(self.genelist_txt_path),
            "entrez_map_csv_path": str(self.entrez_map_csv_path),
            "output_dir": str(self.output_dir),
            "kegg_txt_path": str(self.kegg_txt_path),
            "kegg_png_path": str(self.kegg_png_path),
            "go_txt_path": str(self.go_txt_path),
            "go_png_path": str(self.go_png_path),
            "mapping_summary_path": str(self.mapping_summary_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunGeneFunctionAnnotationTool(PlinkToolBase, Tool):
    """Run maize GO/KEGG enrichment from a gene list and built-in ENTREZ mapping CSV."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="gene_function_annotation_analysis",
            default_output_subdir="gene_function_annotation",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "gene_function_annotation.sh"
        self.r_script_path = self.skill_dir / "run_gene_function_annotation.R"
        self.summary_script_path = self.skill_dir / "summarize_gene_function_annotation.py"
        self.builtin_entrez_map_csv_path = self.skill_dir / "entrez_Zm_gene_v4.csv"

    @property
    def name(self) -> str:
        return "run_gene_function_annotation"

    @property
    def description(self) -> str:
        return (
            "Run maize KEGG and GO enrichment in EasyGS_1 from a user-provided gene list TXT, "
            "using a built-in Zm V4 gene-to-ENTREZ CSV bundled with this skill."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "genelist_txt": {
                    "type": "string",
                    "description": (
                        "User-provided gene list TXT file with one gene ID per line. Example:\n"
                        "Zm00001d031939\n"
                        "Zm00001d031940\n"
                        "Zm00001d031941\n"
                        "Zm00001d031942"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Default: workspace/default_results/"
                        "gene_function_annotation/. If you want to override it, please provide it explicitly."
                    ),
                },
                "gene_column": {
                    "type": "string",
                    "description": (
                        "Gene ID column in the built-in maize ENTREZ mapping CSV. "
                        "Default: gene_name. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
                "entrez_column": {
                    "type": "string",
                    "description": (
                        "ENTREZ ID column in the built-in maize ENTREZ mapping CSV. "
                        "Default: ENTREZID. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
                "annotationhub_id": {
                    "type": "string",
                    "description": (
                        "Required AnnotationHub OrgDb resource ID used for GO enrichment. "
                        "Recommended default: AH119718. Even if you want to use the default, "
                        "please provide it explicitly."
                    ),
                },
                "kegg_organism": {
                    "type": "string",
                    "description": (
                        "KEGG organism code passed to enrichKEGG. This tool currently supports "
                        "maize only, so this value must be zma. Default: zma."
                    ),
                },
                "go_ontology": {
                    "type": "string",
                    "enum": ["BP", "CC", "MF", "ALL"],
                    "description": (
                        "GO ontology passed to enrichGO. Default: ALL. If you want to override it, "
                        "please provide it explicitly."
                    ),
                },
                "kegg_pvalue_threshold": {
                    "type": "number",
                    "description": (
                        "Post-filter p-value threshold for KEGG results. Default: 0.1. If you want "
                        "to override it, please provide it explicitly."
                    ),
                },
                "go_pvalue_threshold": {
                    "type": "number",
                    "description": (
                        "Post-filter p-value threshold for GO results. Default: 0.05. If you want "
                        "to override it, please provide it explicitly."
                    ),
                },
            },
            "required": ["genelist_txt", "annotationhub_id"],
        }

    async def execute(
        self,
        genelist_txt: str,
        annotationhub_id: str,
        output_dir: str | None = None,
        gene_column: str | None = None,
        entrez_column: str | None = None,
        kegg_organism: str | None = None,
        go_ontology: str | None = None,
        kegg_pvalue_threshold: float | None = None,
        go_pvalue_threshold: float | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                genelist_txt=genelist_txt,
                output_dir=output_dir,
                gene_column=gene_column,
                entrez_column=entrez_column,
                annotationhub_id=annotationhub_id,
                kegg_organism=kegg_organism,
                go_ontology=go_ontology,
                kegg_pvalue_threshold=kegg_pvalue_threshold,
                go_pvalue_threshold=go_pvalue_threshold,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Gene function annotation failed.\n"
                f"- Gene list: {prepared.genelist_txt_path}\n"
                f"- Built-in ENTREZ map: {prepared.entrez_map_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Gene function annotation completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Gene list: {prepared.genelist_txt_path}",
            f"- Built-in ENTREZ map: {prepared.entrez_map_csv_path}",
            f"- Gene column: {prepared.gene_column}",
            f"- ENTREZ column: {prepared.entrez_column}",
            f"- AnnotationHub ID: {prepared.annotationhub_id}",
            f"- KEGG organism: {prepared.kegg_organism}",
            f"- GO ontology: {prepared.go_ontology}",
            f"- KEGG threshold: {prepared.kegg_pvalue_threshold}",
            f"- GO threshold: {prepared.go_pvalue_threshold}",
            f"- Output dir: {prepared.output_dir}",
            f"- KEGG TXT: {prepared.kegg_txt_path}",
            f"- KEGG PNG: {prepared.kegg_png_path}",
            f"- GO TXT: {prepared.go_txt_path}",
            f"- GO PNG: {prepared.go_png_path}",
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
        annotationhub_id: str,
        output_dir: str | None = None,
        gene_column: str | None = None,
        entrez_column: str | None = None,
        kegg_organism: str | None = None,
        go_ontology: str | None = None,
        kegg_pvalue_threshold: float | None = None,
        go_pvalue_threshold: float | None = None,
    ) -> PreparedGeneFunctionAnnotationRun:
        genelist_txt_path = self._resolve_gene_list(genelist_txt)
        entrez_map_csv_path = self._resolve_builtin_entrez_map()
        output_root = self._resolve_output_dir(output_dir)

        gene_column_value = (gene_column or "gene_name").strip() or "gene_name"
        entrez_column_value = (entrez_column or "ENTREZID").strip() or "ENTREZID"
        annotationhub_id_value = annotationhub_id.strip()
        if not annotationhub_id_value:
            raise ValueError(
                "annotationhub_id is required. Recommended default: AH119718. "
                "Please provide it explicitly."
            )
        kegg_organism_value = ((kegg_organism or "zma").strip() or "zma").lower()
        if kegg_organism_value != "zma":
            raise ValueError(
                "This tool currently supports maize only, so kegg_organism must be 'zma'."
            )
        go_ontology_value = (go_ontology or "ALL").strip().upper() or "ALL"
        if go_ontology_value not in {"BP", "CC", "MF", "ALL"}:
            raise ValueError("go_ontology must be one of: BP, CC, MF, ALL")

        kegg_pvalue_threshold_value = float(kegg_pvalue_threshold if kegg_pvalue_threshold is not None else 0.1)
        go_pvalue_threshold_value = float(go_pvalue_threshold if go_pvalue_threshold is not None else 0.05)
        for label, value in (
            ("kegg_pvalue_threshold", kegg_pvalue_threshold_value),
            ("go_pvalue_threshold", go_pvalue_threshold_value),
        ):
            if value < 0 or value > 1:
                raise ValueError(f"{label} must be between 0 and 1")

        self._validate_entrez_map_columns(entrez_map_csv_path, gene_column_value, entrez_column_value)

        kegg_txt_path = output_root / "KEGG_Enrichment_Results.txt"
        kegg_png_path = output_root / "KEGG_Enrichment_Results.png"
        go_txt_path = output_root / "GO_Enrichment_Results.txt"
        go_png_path = output_root / "GO_Enrichment_Results.png"
        mapping_summary_path = output_root / "mapping_summary.tsv"
        summary_path = output_root / "gene_function_annotation_summary.txt"

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
            "--genelist-txt",
            str(genelist_txt_path),
            "--entrez-map-csv",
            str(entrez_map_csv_path),
            "--gene-column",
            gene_column_value,
            "--entrez-column",
            entrez_column_value,
            "--annotationhub-id",
            annotationhub_id_value,
            "--kegg-organism",
            kegg_organism_value,
            "--go-ontology",
            go_ontology_value,
            "--kegg-pvalue-threshold",
            str(kegg_pvalue_threshold_value),
            "--go-pvalue-threshold",
            str(go_pvalue_threshold_value),
            "--kegg-txt-output",
            str(kegg_txt_path),
            "--kegg-png-output",
            str(kegg_png_path),
            "--go-txt-output",
            str(go_txt_path),
            "--go-png-output",
            str(go_png_path),
            "--mapping-summary-output",
            str(mapping_summary_path),
            "--summary-output",
            str(summary_path),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedGeneFunctionAnnotationRun(
            launcher=env_status["launcher"],
            gene_column=gene_column_value,
            entrez_column=entrez_column_value,
            annotationhub_id=annotationhub_id_value,
            kegg_organism=kegg_organism_value,
            go_ontology=go_ontology_value,
            kegg_pvalue_threshold=kegg_pvalue_threshold_value,
            go_pvalue_threshold=go_pvalue_threshold_value,
            command=command,
            genelist_txt_path=genelist_txt_path,
            entrez_map_csv_path=entrez_map_csv_path,
            output_dir=output_root,
            kegg_txt_path=kegg_txt_path,
            kegg_png_path=kegg_png_path,
            go_txt_path=go_txt_path,
            go_png_path=go_png_path,
            mapping_summary_path=mapping_summary_path,
            summary_path=summary_path,
        )

    def _resolve_gene_list(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"Gene list file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Gene list input must be a file: {path}")
        preview_lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        if not preview_lines:
            raise ValueError(f"Gene list file is empty: {path}")
        return path

    def _resolve_builtin_entrez_map(self) -> Path:
        path = self.builtin_entrez_map_csv_path
        if not path.exists():
            raise ValueError(f"Built-in maize ENTREZ mapping CSV not found: {path}")
        if not path.is_file():
            raise ValueError(f"Built-in maize ENTREZ mapping path must be a file: {path}")
        if path.suffix.lower() != ".csv":
            raise ValueError(f"Built-in maize ENTREZ mapping input must end with .csv: {path}")
        return path

    def _validate_entrez_map_columns(self, path: Path, gene_column: str, entrez_column: str) -> None:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = [self._normalize_column_name(name) for name in (reader.fieldnames or [])]
            missing = [
                name
                for name in (
                    self._normalize_column_name(gene_column),
                    self._normalize_column_name(entrez_column),
                )
                if name not in fieldnames
            ]
            if missing:
                raise ValueError(
                    f"ENTREZ mapping CSV is missing required columns {missing}: {path}"
                )

    def _normalize_column_name(self, value: str) -> str:
        return value.replace("\ufeff", "").strip()
