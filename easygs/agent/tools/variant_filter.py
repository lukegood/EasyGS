"""Standalone PLINK variant-filter analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedVariantFilterRun:
    """Prepared PLINK variant-filter execution plan."""

    launcher: str
    bed_prefix_name: str
    vcf_prefix_name: str
    command: list[str]
    vcf_path: Path
    output_dir: Path
    bed_prefix_path: Path
    vcf_prefix_path: Path
    filtered_vcf_gz_path: Path
    filtered_vcf_tbi_path: Path
    summary_path: Path
    mind: float
    geno: float
    hwe: float
    maf: float
    link_dir: Path | None
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "vcf_path": str(self.vcf_path),
            "output_dir": str(self.output_dir),
            "bed_prefix_name": self.bed_prefix_name,
            "vcf_prefix_name": self.vcf_prefix_name,
            "bed_prefix_path": str(self.bed_prefix_path),
            "vcf_prefix_path": str(self.vcf_prefix_path),
            "filtered_vcf_gz_path": str(self.filtered_vcf_gz_path),
            "filtered_vcf_tbi_path": str(self.filtered_vcf_tbi_path),
            "summary_path": str(self.summary_path),
            "mind": self.mind,
            "geno": self.geno,
            "hwe": self.hwe,
            "maf": self.maf,
            "link_dir": str(self.link_dir) if self.link_dir else "",
            "notes": list(self.notes),
        }



class RunVariantFilterTool(PlinkToolBase, Tool):
    """Run PLINK-based variant filtering and export filtered VCF output."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="variant_filter_analysis",
            default_output_subdir="variant_filter",
        )
        self.script_path = self.skill_dir / "filter.sh"
        self.summary_script_path = self.skill_dir / "summarize_filter.py"

    @property
    def name(self) -> str:
        return "run_variant_filter"

    @property
    def description(self) -> str:
        return (
            "Filter variants and samples with PLINK, export a filtered VCF.GZ, and build "
            "a summary report using the EasyGS_2 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {"type": "string", "description": "User-provided path to the input VCF or VCF.GZ file."},
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/variant_filter/."
                    ),
                },
                "bed_prefix": {
                    "type": "string",
                    "description": "Basename for PLINK BED outputs. Defaults to 'filtered'.",
                },
                "vcf_prefix": {
                    "type": "string",
                    "description": "Basename for filtered VCF outputs. Defaults to 'filter'.",
                },
                "mind": {"type": "number", "description": "Sample missingness threshold for PLINK --mind."},
                "geno": {"type": "number", "description": "Variant missingness threshold for PLINK --geno."},
                "hwe": {"type": "number", "description": "Hardy-Weinberg equilibrium p-value threshold for --hwe."},
                "maf": {"type": "number", "description": "Minor allele frequency threshold for PLINK --maf."},
                "link_dir": {
                    "type": "string",
                    "description": "Optional directory where filtered VCF.GZ and index symlinks should be created.",
                },
                "bgzip_output": {
                    "type": "boolean",
                    "description": "Whether to bgzip the exported filtered VCF. Defaults to true.",
                },
                "tabix_index": {
                    "type": "boolean",
                    "description": "Whether to create a tabix index for the filtered VCF.GZ. Defaults to true.",
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        output_dir: str | None = None,
        bed_prefix: str = "filtered",
        vcf_prefix: str = "filter",
        mind: float = 0.05,
        geno: float = 0.05,
        hwe: float = 1e-4,
        maf: float = 0.0001,
        link_dir: str | None = None,
        bgzip_output: bool = True,
        tabix_index: bool = True,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                output_dir=output_dir,
                bed_prefix=bed_prefix,
                vcf_prefix=vcf_prefix,
                mind=mind,
                geno=geno,
                hwe=hwe,
                maf=maf,
                link_dir=link_dir,
                bgzip_output=bgzip_output,
                tabix_index=tabix_index,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Variant filtering failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"- BED prefix: {prepared.bed_prefix_path}\n"
                f"- VCF prefix: {prepared.vcf_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Variant filtering completed.",
            f"- Launcher: {prepared.launcher}",
            f"- VCF: {prepared.vcf_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- BED prefix: {prepared.bed_prefix_path}",
            f"- Filtered VCF.GZ: {prepared.filtered_vcf_gz_path}",
            f"- Tabix index: {prepared.filtered_vcf_tbi_path}",
            f"- Summary file: {prepared.summary_path}",
        ]
        if prepared.link_dir:
            lines.append(f"- Link dir: {prepared.link_dir}")
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
        output_dir: str | None = None,
        bed_prefix: str = "filtered",
        vcf_prefix: str = "filter",
        mind: float = 0.05,
        geno: float = 0.05,
        hwe: float = 1e-4,
        maf: float = 0.0001,
        link_dir: str | None = None,
        bgzip_output: bool = True,
        tabix_index: bool = True,
    ) -> PreparedVariantFilterRun:
        if tabix_index and not bgzip_output:
            raise ValueError("tabix_index=true requires bgzip_output=true")

        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)
        link_dir_path = _resolve_path(link_dir, self.allowed_dir) if link_dir else None

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        required_tools = ["plink"]
        if bgzip_output:
            required_tools.append("bgzip")
        if tabix_index:
            required_tools.append("tabix")
        env_status = await self._get_environment_status(required_tools)
        if env_status["error"]:
            error = env_status["error"]
            raise ValueError(error[7:] if error.startswith("Error: ") else error)

        bed_prefix_name = self._normalize_prefix_name(bed_prefix, "filtered")
        vcf_prefix_name = self._normalize_prefix_name(vcf_prefix, "filter")
        bed_prefix_path = output_root / bed_prefix_name
        vcf_prefix_path = output_root / vcf_prefix_name
        summary_path = output_root / f"{vcf_prefix_name}_summary.txt"
        filtered_vcf_gz_path = vcf_prefix_path.with_suffix(".vcf.gz")
        filtered_vcf_tbi_path = output_root / f"{vcf_prefix_name}.vcf.gz.tbi"

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "bash",
            str(self.script_path),
            "--vcf",
            str(vcf_path),
            "--out-dir",
            str(output_root),
            "--bed-prefix",
            bed_prefix_name,
            "--vcf-prefix",
            vcf_prefix_name,
            "--mind",
            str(mind),
            "--geno",
            str(geno),
            "--hwe",
            str(hwe),
            "--maf",
            str(maf),
            "--bgzip-output",
            "1" if bgzip_output else "0",
            "--tabix-index",
            "1" if tabix_index else "0",
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if link_dir_path:
            command.extend(["--link-dir", str(link_dir_path)])

        return PreparedVariantFilterRun(
            launcher=env_status["launcher"],
            bed_prefix_name=bed_prefix_name,
            vcf_prefix_name=vcf_prefix_name,
            command=command,
            vcf_path=vcf_path,
            output_dir=output_root,
            bed_prefix_path=bed_prefix_path,
            vcf_prefix_path=vcf_prefix_path,
            filtered_vcf_gz_path=filtered_vcf_gz_path,
            filtered_vcf_tbi_path=filtered_vcf_tbi_path,
            summary_path=summary_path,
            mind=mind,
            geno=geno,
            hwe=hwe,
            maf=maf,
            link_dir=link_dir_path,
        )
