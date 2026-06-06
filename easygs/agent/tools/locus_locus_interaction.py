"""Gene-by-gene interaction analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedLocusLocusInteractionRun:
    """Prepared execution plan for gene-by-gene interaction analysis."""

    launcher: str
    prefix: str
    threshold: float
    command: list[str]
    vcf_path: Path
    phenotype_csv_path: Path
    gene_map_path: Path
    output_dir: Path
    summary_csv_path: Path
    detailed_csv_path: Path
    report_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "threshold": self.threshold,
            "vcf_path": str(self.vcf_path),
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "gene_map_path": str(self.gene_map_path),
            "output_dir": str(self.output_dir),
            "summary_csv_path": str(self.summary_csv_path),
            "detailed_csv_path": str(self.detailed_csv_path),
            "report_path": str(self.report_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunLocusLocusInteractionTool(PlinkToolBase, Tool):
    """Run the bundled gene-by-gene interaction workflow from VCF, phenotype, and gene map."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="locus_locus_interaction_analysis",
            default_output_subdir="locus_locus_interaction",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "locus_locus_interaction.sh"
        self.python_script_path = self.skill_dir / "run_locus_locus_interaction.py"
        self.summary_script_path = self.skill_dir / "summarize_locus_locus_interaction.py"

    @property
    def name(self) -> str:
        return "run_locus_locus_interaction"

    @property
    def description(self) -> str:
        return (
            "Run gene-by-gene interaction analysis from a VCF file, a phenotype CSV with "
            "ID and Phenotype columns, and a locus-to-gene mapping text file, then export "
            "significant gene pairs and detailed SNP-pair interactions."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {
                    "type": "string",
                    "description": (
                        "Input genotype file in .vcf or .vcf.gz format. Variant IDs must be "
                        "present in the VCF ID field. Example:\n"
                        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tMG_49\tMG_50\n"
                        "1\t201492\tchr1.s_201492\tA\tG\t.\tPASS\t.\tGT\t0/0\t0/1"
                    ),
                },
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Input phenotype CSV containing ID and Phenotype columns. Example:\n"
                        "ID,Phenotype\n"
                        "MG_49,234.6\n"
                        "MG_50,217.2\n"
                        "MG_51,198.5\n"
                        "MG_52,209.8"
                    ),
                },
                "gene_map": {
                    "type": "string",
                    "description": (
                        "Input locus-to-gene mapping text file. Each row should contain a locus ID "
                        "and a gene name separated by tab, comma, or spaces. Example:\n"
                        "chr1.s_201492\tZm00001d027240\n"
                        "chr1.s_692383\tZm00001d027259\n"
                        "chr1.s_1022873\tZm00001d027265\n"
                        "chr1.s_1069916\tZm00001d027271"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional root output directory. Results are written into "
                        "<output_dir>/<prefix>/. If omitted, foreground runs default to "
                        "workspace/default_results/locus_locus_interaction/<prefix>/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Output folder name under the root output directory. Defaults to "
                        "'gene_interaction_results'."
                    ),
                },
                "threshold": {
                    "type": "number",
                    "description": (
                        "FDR significance threshold used to keep gene pairs. Defaults to 0.05."
                    ),
                    "exclusiveMinimum": 0,
                },
            },
            "required": ["vcf", "phenotype_csv", "gene_map"],
        }

    async def execute(
        self,
        vcf: str,
        phenotype_csv: str,
        gene_map: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> str:
        legacy_threshold = kwargs.get("pvalue_threshold")
        if threshold is None and legacy_threshold is not None:
            threshold = legacy_threshold
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                phenotype_csv=phenotype_csv,
                gene_map=gene_map,
                output_dir=output_dir,
                prefix=prefix,
                threshold=threshold,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Gene-by-gene interaction analysis failed.\n"
                f"- Input VCF: {prepared.vcf_path}\n"
                f"- Phenotype CSV: {prepared.phenotype_csv_path}\n"
                f"- Gene map: {prepared.gene_map_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Gene-by-gene interaction analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Phenotype CSV: {prepared.phenotype_csv_path}",
            f"- Gene map: {prepared.gene_map_path}",
            f"- Threshold: {prepared.threshold}",
            f"- Output dir: {prepared.output_dir}",
            f"- Summary CSV: {prepared.summary_csv_path}",
            f"- Detailed SNP-pair CSV: {prepared.detailed_csv_path}",
            f"- Analysis report: {prepared.report_path}",
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
        vcf: str,
        phenotype_csv: str,
        gene_map: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        threshold: float | None = None,
    ) -> PreparedLocusLocusInteractionRun:
        vcf_path = self._resolve_vcf(vcf)
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv, "Phenotype CSV")
        gene_map_path = self._resolve_text_file(gene_map, "Gene mapping file")

        prefix_name = self._normalize_name(prefix, "gene_interaction_results", "prefix")
        threshold_value = 0.05 if threshold is None else float(threshold)
        if threshold_value <= 0:
            raise ValueError("threshold must be greater than 0")

        output_root = self._resolve_output_dir(output_dir)
        analysis_output_dir = output_root / prefix_name
        summary_csv_path = analysis_output_dir / "gene_interaction_summary.csv"
        detailed_csv_path = analysis_output_dir / "significant_snp_pairs_detailed.csv"
        report_path = analysis_output_dir / "analysis_report.txt"
        summary_path = analysis_output_dir / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "Python script": self.python_script_path,
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
            "--vcf",
            str(vcf_path),
            "--phenotype-csv",
            str(phenotype_csv_path),
            "--gene-map",
            str(gene_map_path),
            "--output-dir",
            str(analysis_output_dir),
            "--threshold",
            str(threshold_value),
            "--summary-output",
            str(summary_path),
            "--python-script",
            str(self.python_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedLocusLocusInteractionRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            threshold=threshold_value,
            command=command,
            vcf_path=vcf_path,
            phenotype_csv_path=phenotype_csv_path,
            gene_map_path=gene_map_path,
            output_dir=analysis_output_dir,
            summary_csv_path=summary_csv_path,
            detailed_csv_path=detailed_csv_path,
            report_path=report_path,
            summary_path=summary_path,
        )

    def _resolve_csv_file(self, value: str, label: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"{label} not found: {path}")
        if not path.is_file():
            raise ValueError(f"{label} must be a file: {path}")
        if path.suffix.lower() != ".csv":
            raise ValueError(f"{label} must end with .csv: {path}")
        return path

    def _resolve_text_file(self, value: str, label: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"{label} not found: {path}")
        if not path.is_file():
            raise ValueError(f"{label} must be a file: {path}")
        return path

    def _normalize_name(self, value: str | None, default: str, field_name: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            candidate = default
        if "/" in candidate or "\\" in candidate:
            raise ValueError(f"{field_name} must not contain path separators: {candidate}")
        return candidate
