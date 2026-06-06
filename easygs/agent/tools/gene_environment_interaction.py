"""Gene-by-environment interaction analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedGeneEnvironmentInteractionRun:
    """Prepared execution plan for gene-by-environment interaction analysis."""

    launcher: str
    prefix: str
    group_size: int
    max_workers: int | None
    command: list[str]
    vcf_path: Path
    phenotype_csv_path: Path
    env_csv_path: Path
    output_dir: Path
    env_factor_dir_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "group_size": self.group_size,
            "max_workers": self.max_workers,
            "vcf_path": str(self.vcf_path),
            "phenotype_csv_path": str(self.phenotype_csv_path),
            "env_csv_path": str(self.env_csv_path),
            "output_dir": str(self.output_dir),
            "env_factor_dir_path": str(self.env_factor_dir_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunGeneEnvironmentInteractionTool(PlinkToolBase, Tool):
    """Run a bundled GxE ANOVA workflow from VCF, phenotype, and environment tables."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="gene_environment_interaction_analysis",
            default_output_subdir="gene_environment_interaction",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "gene_environment_interaction.sh"
        self.python_script_path = self.skill_dir / "run_gene_environment_interaction.py"
        self.summary_script_path = self.skill_dir / "summarize_gene_environment_interaction.py"

    @property
    def name(self) -> str:
        return "run_gene_environment_interaction"

    @property
    def description(self) -> str:
        return (
            "Run SNP-by-environment-factor interaction ANOVA from a VCF file, a wide "
            "phenotype CSV, and a region-level environment-factor mean CSV, then write "
            "one interaction result file per environmental factor across all TraitEnv columns."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {
                    "type": "string",
                    "description": (
                        "Input genotype file in .vcf or .vcf.gz format. Sample IDs in the VCF "
                        "must match the phenotype ID column. Example:\n"
                        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tMG_1000\tMG_1001\tMG_1002\n"
                        "1\t1067986\tchr1.s_1067986\tA\tA\t.\tPASS\t.\tGT\t0/0\t0/0\t0/0"
                    ),
                },
                "phenotype_csv": {
                    "type": "string",
                    "description": (
                        "Input phenotype CSV in wide format. The first column must be ID, and "
                        "regional phenotype columns should use '<trait>_<env>' names. Example:\n"
                        "ID,PH_JL,PH_LN,PH_BJ,PH_HB,PH_HN\n"
                        "MG_49,234.6,241.13,249.6,228.8,215.25\n"
                        "MG_50,217.2,204,212.2,196.75,173.6\n"
                        "MG_51,198.5,207.4,202.75,233.33,166.2\n"
                        "MG_52,209.8,230.5,209.8,189.4,184.5\n"
                        "MG_53,219.2,200,224.25,183.75,182.25"
                    ),
                },
                "env_csv": {
                    "type": "string",
                    "description": (
                        "Input region-level environment-factor mean CSV. The first column stores "
                        "environment IDs such as BJ/HB/HN/JL/LN, followed by environmental factor "
                        "columns. Example:\n"
                        "env,DL,GDD,dGDD,DTR,PTT\n"
                        "BJ,13.9308666666667,24.57782,2.75673333333333,23.15124,348.419468666667\n"
                        "HB,13.1262133333333,24.3513666666667,2.51986,22.6752,333.167522666667\n"
                        "HN,12.9729866666667,25.2959933333333,2.52274666666667,20.48088,340.244692666667\n"
                        "JL,14.3564933333333,17.60544,2.36148,21.62916,257.755178\n"
                        "LN,14.0801933333333,21.50472,2.55774,22.95036,307.263327333333"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional root output directory. Results are written into "
                        "<output_dir>/<prefix>/. If omitted, foreground runs default to "
                        "workspace/default_results/gene_environment_interaction/<prefix>/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Output folder name under the root output directory. Defaults to "
                        "'gene_env_huzuo_ANOVA'."
                    ),
                },
                "group_size": {
                    "type": "integer",
                    "description": "Number of SNPs analyzed per group. Defaults to 1.",
                    "minimum": 1,
                },
                "max_workers": {
                    "type": "integer",
                    "description": (
                        "Optional worker count for parallel SNP-group processing. Defaults to "
                        "the available CPU count inside EasyGS_1."
                    ),
                    "minimum": 1,
                },
            },
            "required": ["vcf", "phenotype_csv", "env_csv"],
        }

    async def execute(
        self,
        vcf: str,
        phenotype_csv: str,
        env_csv: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        group_size: int | None = None,
        max_workers: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                phenotype_csv=phenotype_csv,
                env_csv=env_csv,
                output_dir=output_dir,
                prefix=prefix,
                group_size=group_size,
                max_workers=max_workers,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Gene-by-environment interaction analysis failed.\n"
                f"- Input VCF: {prepared.vcf_path}\n"
                f"- Phenotype CSV: {prepared.phenotype_csv_path}\n"
                f"- Environment CSV: {prepared.env_csv_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Gene-by-environment interaction analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Phenotype CSV: {prepared.phenotype_csv_path}",
            f"- Environment CSV: {prepared.env_csv_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Env-factor result dir: {prepared.env_factor_dir_path}",
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
        env_csv: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        group_size: int | None = None,
        max_workers: int | None = None,
    ) -> PreparedGeneEnvironmentInteractionRun:
        vcf_path = self._resolve_vcf(vcf)
        phenotype_csv_path = self._resolve_csv_file(phenotype_csv, "Phenotype CSV")
        env_csv_path = self._resolve_csv_file(env_csv, "Environment CSV")

        prefix_name = self._normalize_name(prefix, "gene_env_huzuo_ANOVA", "prefix")

        output_root = self._resolve_output_dir(output_dir)
        analysis_output_dir = output_root / prefix_name
        env_factor_dir_path = analysis_output_dir / "env_factors"
        summary_path = analysis_output_dir / f"{prefix_name}_summary.txt"

        group_size_value = 1 if group_size is None else int(group_size)
        if group_size_value < 1:
            raise ValueError("group_size must be at least 1")

        max_workers_value = None if max_workers is None else int(max_workers)
        if max_workers_value is not None and max_workers_value < 1:
            raise ValueError("max_workers must be at least 1 when provided")

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
            "--env-csv",
            str(env_csv_path),
            "--output-dir",
            str(analysis_output_dir),
            "--group-size",
            str(group_size_value),
            "--summary-output",
            str(summary_path),
            "--python-script",
            str(self.python_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if max_workers_value is not None:
            command.extend(["--max-workers", str(max_workers_value)])

        return PreparedGeneEnvironmentInteractionRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            group_size=group_size_value,
            max_workers=max_workers_value,
            command=command,
            vcf_path=vcf_path,
            phenotype_csv_path=phenotype_csv_path,
            env_csv_path=env_csv_path,
            output_dir=analysis_output_dir,
            env_factor_dir_path=env_factor_dir_path,
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

    def _normalize_name(self, value: str | None, default: str, field_name: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            candidate = default
        if "/" in candidate or "\\" in candidate:
            raise ValueError(f"{field_name} must not contain path separators: {candidate}")
        return candidate
