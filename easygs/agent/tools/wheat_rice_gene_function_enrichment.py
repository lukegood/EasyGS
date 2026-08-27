"""Offline GO/KEGG enrichment for wheat and rice using user-managed resources."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
from easygs.resources import resolve_user_resource_path

_RESOURCE_FILES = {
    "wheat": {
        "gene2ko": "wheat_gene_KO_one2one.tsv",
        "kegg_annotation": "taes_KEGG_annotation.txt",
        "gene2go": "wheat_gene_GO_one2one.tsv",
    },
    "rice": {
        "gene2ko": "rice_gene_KO_one2one.tsv",
        "kegg_annotation": "rice_KEGG_annotation.txt",
        "gene2go": "rice_gene_GO_one2one.tsv",
    },
}
_GO_TERM_FILENAME = "GO_term_table_2026.7.16.tsv"


@dataclass
class PreparedWheatRiceGeneFunctionEnrichmentRun:
    """Prepared execution plan for wheat/rice GO and KEGG enrichment."""

    launcher: str
    species: str
    analysis_type: str
    command: list[str]
    genelist_txt_path: Path
    resource_dir: Path
    output_dir: Path
    output_prefix: str
    summary_path: Path
    gene2ko_path: Path | None = None
    kegg_annotation_path: Path | None = None
    gene2go_path: Path | None = None
    go_term_path: Path | None = None
    kegg_all_path: Path | None = None
    kegg_significant_path: Path | None = None
    kegg_mapped_gene_path: Path | None = None
    kegg_plot_path: Path | None = None
    go_all_path: Path | None = None
    go_significant_path: Path | None = None
    go_mapped_gene_path: Path | None = None
    go_plot_path: Path | None = None
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        values = {
            "launcher": self.launcher,
            "species": self.species,
            "analysis_type": self.analysis_type,
            "genelist_txt_path": self.genelist_txt_path,
            "resource_dir": self.resource_dir,
            "output_dir": self.output_dir,
            "output_prefix": self.output_prefix,
            "summary_path": self.summary_path,
            "gene2ko_path": self.gene2ko_path,
            "kegg_annotation_path": self.kegg_annotation_path,
            "gene2go_path": self.gene2go_path,
            "go_term_path": self.go_term_path,
            "kegg_all_path": self.kegg_all_path,
            "kegg_significant_path": self.kegg_significant_path,
            "kegg_mapped_gene_path": self.kegg_mapped_gene_path,
            "kegg_plot_path": self.kegg_plot_path,
            "go_all_path": self.go_all_path,
            "go_significant_path": self.go_significant_path,
            "go_mapped_gene_path": self.go_mapped_gene_path,
            "go_plot_path": self.go_plot_path,
        }
        metadata = {
            key: (str(value) if isinstance(value, Path) else value)
            for key, value in values.items()
            if value is not None
        }
        metadata["notes"] = list(self.notes)
        return metadata


class RunWheatRiceGeneFunctionEnrichmentTool(PlinkToolBase, Tool):
    """Run offline GO/KEGG enrichment for wheat or rice."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="wheat_rice_gene_function_enrichment_analysis",
            default_output_subdir="wheat_rice_gene_function_enrichment",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "gene_function_enrichment.sh"
        self.kegg_r_script_path = self.skill_dir / "run_kegg_enrichment.R"
        self.go_r_script_path = self.skill_dir / "run_go_enrichment.R"
        self.summary_script_path = self.skill_dir / "summarize_gene_function_enrichment.py"
        self.resource_dir = resolve_user_resource_path(
            "wheat_rice_gene_function_enrichment_analysis"
        )

    @property
    def name(self) -> str:
        return "run_wheat_rice_gene_function_enrichment"

    @property
    def description(self) -> str:
        return (
            "Run offline GO and/or KEGG enrichment for wheat or rice in EasyGS_1 from a "
            "user-provided gene list. Species-specific gene-to-GO/KO and annotation databases "
            "are read automatically from the EasyGS user resource directory."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "genelist_txt": {
                    "type": "string",
                    "description": (
                        "User-provided gene list TXT with one gene ID per line. Wheat example:\n"
                        "TraesCS6A03G0926000\nTraesCS3D03G0591600\nTraesCS3B03G0806700\n"
                        "TraesCS1D03G0346300\nRice example:\nLOC_Os02g07880\nLOC_Os01g19750\n"
                        "LOC_Os05g33910\nLOC_Os07g42632"
                    ),
                },
                "species": {
                    "type": "string",
                    "enum": ["wheat", "rice"],
                    "description": "Required species used to select the matching EasyGS resources.",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["ALL", "GO", "KEGG"],
                    "description": (
                        "Analysis branch to run. Default: ALL. Use GO or KEGG only when the user "
                        "explicitly requests one branch."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Default: workspace/default_results/"
                        "wheat_rice_gene_function_enrichment/."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional common result prefix. Default: the selected species name. "
                        "For example, wheat produces wheat_KEGG_* and wheat_GO_* files."
                    ),
                },
            },
            "required": ["genelist_txt", "species"],
        }

    async def execute(
        self,
        genelist_txt: str,
        species: str,
        analysis_type: str | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                genelist_txt=genelist_txt,
                species=species,
                analysis_type=analysis_type,
                output_dir=output_dir,
                output_prefix=output_prefix,
            )
        except (PermissionError, ValueError) as exc:
            return f"Error: {exc}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Wheat/rice gene function enrichment failed.\n"
                f"- Species: {prepared.species}\n"
                f"- Analysis type: {prepared.analysis_type}\n"
                f"- Gene list: {prepared.genelist_txt_path}\n"
                f"- Resource dir: {prepared.resource_dir}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Wheat/rice gene function enrichment completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Species: {prepared.species}",
            f"- Analysis type: {prepared.analysis_type}",
            f"- Gene list: {prepared.genelist_txt_path}",
            f"- Resource dir: {prepared.resource_dir}",
            f"- Output dir: {prepared.output_dir}",
        ]
        for label, path in self._result_paths(prepared):
            lines.append(f"- {label}: {path}")
        lines.append(f"- Summary file: {prepared.summary_path}")

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
        species: str,
        analysis_type: str | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
    ) -> PreparedWheatRiceGeneFunctionEnrichmentRun:
        species_value = (species or "").strip().lower()
        if species_value not in _RESOURCE_FILES:
            raise ValueError("species must be one of: wheat, rice")

        analysis_type_value = (analysis_type or "ALL").strip().upper() or "ALL"
        if analysis_type_value not in {"ALL", "GO", "KEGG"}:
            raise ValueError("analysis_type must be one of: ALL, GO, KEGG")

        genelist_txt_path = self._resolve_gene_list(genelist_txt)
        output_root = self._resolve_output_dir(output_dir)
        output_prefix_value = self._validate_output_prefix(output_prefix, species_value)
        summary_path = output_root / f"{output_prefix_value}_gene_function_enrichment_summary.txt"

        run_kegg = analysis_type_value in {"ALL", "KEGG"}
        run_go = analysis_type_value in {"ALL", "GO"}
        resource_names = _RESOURCE_FILES[species_value]

        gene2ko_path = None
        kegg_annotation_path = None
        kegg_all_path = None
        kegg_significant_path = None
        kegg_mapped_gene_path = None
        kegg_plot_path = None
        if run_kegg:
            gene2ko_path = self._resolve_resource(
                resource_names["gene2ko"],
                required_columns=("locusName", "KO"),
                label=f"{species_value} gene-to-KO resource",
            )
            kegg_annotation_path = self._resolve_resource(
                resource_names["kegg_annotation"],
                required_columns=("KO", "Pathway_ID", "Pathway_Name"),
                label=f"{species_value} KEGG annotation resource",
            )
            kegg_prefix = output_root / f"{output_prefix_value}_KEGG"
            kegg_all_path = Path(f"{kegg_prefix}_KEGG_enrichment_all_p1.0.tsv")
            kegg_significant_path = Path(
                f"{kegg_prefix}_KEGG_enrichment_significant_p0.1.tsv"
            )
            kegg_mapped_gene_path = Path(f"{kegg_prefix}_Mapped_gene.txt")
            kegg_plot_path = Path(f"{kegg_prefix}_KEGG_enrichment_custom.png")

        gene2go_path = None
        go_term_path = None
        go_all_path = None
        go_significant_path = None
        go_mapped_gene_path = None
        go_plot_path = None
        if run_go:
            gene2go_path = self._resolve_resource(
                resource_names["gene2go"],
                required_columns=("locusName", "GO"),
                label=f"{species_value} gene-to-GO resource",
            )
            go_term_path = self._resolve_resource(
                _GO_TERM_FILENAME,
                required_columns=("GOID", "TERM", "ONTOLOGY"),
                label="GO term resource",
            )
            go_prefix = output_root / f"{output_prefix_value}_GO"
            go_all_path = Path(f"{go_prefix}_GO_enrichment_all_p1.0.tsv")
            go_significant_path = Path(f"{go_prefix}_GO_enrichment_significant_p0.1.tsv")
            go_mapped_gene_path = Path(f"{go_prefix}_Mapped_gene.txt")
            go_plot_path = Path(f"{go_prefix}_GO_enrichment.png")

        for label, path in {
            "pipeline script": self.script_path,
            "KEGG R script": self.kegg_r_script_path,
            "GO R script": self.go_r_script_path,
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
            "--species",
            species_value,
            "--analysis-type",
            analysis_type_value,
            "--genelist-txt",
            str(genelist_txt_path),
            "--summary-output",
            str(summary_path),
            "--kegg-r-script",
            str(self.kegg_r_script_path),
            "--go-r-script",
            str(self.go_r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if run_kegg:
            command.extend(
                [
                    "--gene2ko-tsv",
                    str(gene2ko_path),
                    "--kegg-annotation-tsv",
                    str(kegg_annotation_path),
                    "--kegg-all-output",
                    str(kegg_all_path),
                    "--kegg-significant-output",
                    str(kegg_significant_path),
                    "--kegg-mapped-output",
                    str(kegg_mapped_gene_path),
                    "--kegg-plot-output",
                    str(kegg_plot_path),
                ]
            )
        if run_go:
            command.extend(
                [
                    "--gene2go-tsv",
                    str(gene2go_path),
                    "--go-term-tsv",
                    str(go_term_path),
                    "--go-all-output",
                    str(go_all_path),
                    "--go-significant-output",
                    str(go_significant_path),
                    "--go-mapped-output",
                    str(go_mapped_gene_path),
                    "--go-plot-output",
                    str(go_plot_path),
                ]
            )

        return PreparedWheatRiceGeneFunctionEnrichmentRun(
            launcher=env_status["launcher"],
            species=species_value,
            analysis_type=analysis_type_value,
            command=command,
            genelist_txt_path=genelist_txt_path,
            resource_dir=self.resource_dir,
            output_dir=output_root,
            output_prefix=output_prefix_value,
            summary_path=summary_path,
            gene2ko_path=gene2ko_path,
            kegg_annotation_path=kegg_annotation_path,
            gene2go_path=gene2go_path,
            go_term_path=go_term_path,
            kegg_all_path=kegg_all_path,
            kegg_significant_path=kegg_significant_path,
            kegg_mapped_gene_path=kegg_mapped_gene_path,
            kegg_plot_path=kegg_plot_path,
            go_all_path=go_all_path,
            go_significant_path=go_significant_path,
            go_mapped_gene_path=go_mapped_gene_path,
            go_plot_path=go_plot_path,
        )

    def _resolve_gene_list(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"Gene list TXT not found: {path}")
        if not path.is_file():
            raise ValueError(f"Gene list TXT must be a file: {path}")
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        if not lines:
            raise ValueError(f"Gene list TXT is empty: {path}")
        return path

    def _resolve_resource(
        self,
        filename: str,
        *,
        required_columns: tuple[str, ...],
        label: str,
    ) -> Path:
        path = self.resource_dir / filename
        if not path.exists():
            raise ValueError(
                "Missing required resource for "
                "wheat_rice_gene_function_enrichment_analysis:\n"
                f"{path}\n\n"
                f"Please prepare {filename} and place it at the path above. "
                "Set EASYGS_RESOURCES_DIR to use a different resource root."
            )
        if not path.is_file():
            raise ValueError(f"{label} must be a file: {path}")
        self._validate_resource_columns(path, required_columns, label)
        return path

    def _validate_resource_columns(
        self,
        path: Path,
        required_columns: tuple[str, ...],
        label: str,
    ) -> None:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            try:
                header = [value.strip() for value in next(reader)]
            except StopIteration as exc:
                raise ValueError(f"{label} is empty: {path}") from exc
            missing = [column for column in required_columns if column not in header]
            if missing:
                raise ValueError(f"{label} is missing required columns {missing}: {path}")
            if not any(any(value.strip() for value in row) for row in reader):
                raise ValueError(f"{label} has no data rows: {path}")

    def _validate_output_prefix(self, value: str | None, species: str) -> str:
        candidate = (value or species).strip() or species
        if candidate in {".", ".."} or Path(candidate).name != candidate or "\\" in candidate:
            raise ValueError("output_prefix must be a filename prefix without directory components")
        return candidate

    def _result_paths(
        self, prepared: PreparedWheatRiceGeneFunctionEnrichmentRun
    ) -> list[tuple[str, Path]]:
        paths = [
            ("KEGG all TSV", prepared.kegg_all_path),
            ("KEGG significant TSV", prepared.kegg_significant_path),
            ("KEGG mapped genes", prepared.kegg_mapped_gene_path),
            ("KEGG PNG", prepared.kegg_plot_path),
            ("GO all TSV", prepared.go_all_path),
            ("GO significant TSV", prepared.go_significant_path),
            ("GO mapped genes", prepared.go_mapped_gene_path),
            ("GO PNG", prepared.go_plot_path),
        ]
        return [(label, path) for label, path in paths if path is not None]
