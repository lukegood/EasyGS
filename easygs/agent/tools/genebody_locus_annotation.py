"""Genebody locus annotation tool using built-in maize V4 gene-body BED."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedGenebodyLocusAnnotationRun:
    """Prepared execution plan for genebody locus annotation."""

    launcher: str
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
            "locus_list_path": str(self.locus_list_path),
            "gene_bed_path": str(self.gene_bed_path),
            "output_dir": str(self.output_dir),
            "site_gene_path": str(self.site_gene_path),
            "gene_list_path": str(self.gene_list_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunGenebodyLocusAnnotationTool(PlinkToolBase, Tool):
    """Annotate loci that fall inside maize V4 gene bodies."""

    _LOCUS_RE = re.compile(r"^(?:chr)?[A-Za-z0-9_]+[.]s_[0-9]+$")

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
        self.gene_bed_path = self.skill_dir / "allV4gene.bed"

    @property
    def name(self) -> str:
        return "run_genebody_locus_annotation"

    @property
    def description(self) -> str:
        return (
            "Annotate loci that fall in maize V4 gene bodies from a TXT locus list using "
            "the built-in allV4gene.bed, then export locus-to-gene pairs and the gene list."
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
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(locus_list=locus_list, output_dir=output_dir)
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Genebody locus annotation failed.\n"
                f"- Locus list: {prepared.locus_list_path}\n"
                f"- Built-in gene BED: {prepared.gene_bed_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Genebody locus annotation completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Locus list: {prepared.locus_list_path}",
            f"- Built-in gene BED: {prepared.gene_bed_path}",
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
        output_dir: str | None = None,
    ) -> PreparedGenebodyLocusAnnotationRun:
        locus_list_path = self._resolve_locus_list(locus_list)
        self._validate_locus_list_preview(locus_list_path)
        output_root = self._resolve_output_dir(output_dir)

        site_gene_path = output_root / "位于genebody的位点及其对应的基因.txt"
        gene_list_path = output_root / "位于genebody的基因.txt"
        summary_path = output_root / "genebody_locus_annotation_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
            "built-in allV4gene.bed": self.gene_bed_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")
            if not path.is_file():
                raise ValueError(f"{label} must be a file: {path}")

        env_status = await self._get_environment_status(["bedtools", "python3", "awk", "sed", "cut"])
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
            "--site-gene-output",
            str(site_gene_path),
            "--gene-output",
            str(gene_list_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--gene-bed",
            str(self.gene_bed_path),
        ]

        return PreparedGenebodyLocusAnnotationRun(
            launcher=env_status["launcher"],
            command=command,
            locus_list_path=locus_list_path,
            gene_bed_path=self.gene_bed_path,
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

    def _validate_locus_list_preview(self, path: Path) -> None:
        valid_rows = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                locus = line.split()[0]
                if not self._LOCUS_RE.match(locus):
                    raise ValueError(
                        "Locus list rows must look like chr1.s_201492 "
                        f"(line {line_number} in {path}: {line})"
                    )
                valid_rows += 1
                if valid_rows >= 5:
                    break
        if valid_rows == 0:
            raise ValueError(f"Locus list does not contain any valid locus rows: {path}")
