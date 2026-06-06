"""GEBV analysis tool backed by a bundled GCTA REML pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedGebvRun:
    """Prepared GEBV execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    grm_prefix_path: Path
    pheno_path: Path
    output_dir: Path
    output_prefix_path: Path
    hsq_path: Path
    blp_path: Path
    log_path: Path
    clean_path: Path
    top_path: Path
    summary_path: Path
    top_percent: int
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "grm_prefix_path": str(self.grm_prefix_path),
            "pheno_path": str(self.pheno_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "hsq_path": str(self.hsq_path),
            "blp_path": str(self.blp_path),
            "log_path": str(self.log_path),
            "clean_path": str(self.clean_path),
            "top_path": str(self.top_path),
            "summary_path": str(self.summary_path),
            "top_percent": self.top_percent,
            "notes": list(self.notes),
        }



class RunGebvTool(PlinkToolBase, Tool):
    """Estimate GEBV values from an existing GRM and phenotype table."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="gebv_analysis",
            default_output_subdir="gebv",
        )
        self.script_path = self.skill_dir / "gebv.sh"
        self.summary_script_path = self.skill_dir / "summarize_gebv.py"

    @property
    def name(self) -> str:
        return "run_gebv"

    @property
    def description(self) -> str:
        return (
            "Run GCTA REML random-effect prediction on an existing GRM prefix and phenotype "
            "file, then extract GEBV values and select the top individuals."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "grm_prefix": {
                    "type": "string",
                    "description": "GCTA GRM prefix without the .grm.bin/.grm.N.bin/.grm.id suffixes.",
                },
                "pheno": {
                    "type": "string",
                    "description": (
                        "Phenotype file passed to GCTA REML for GEBV estimation. "
                        "Use a tab-delimited three-column file with FID, IID, and phenotype value. "
                        "Example:\n"
                        "FID\tIID\tPH\n"
                        "MG_49\tMG_49\t234.6\n"
                        "MG_50\tMG_50\t217.2\n"
                        "MG_51\tMG_51\t198.5\n"
                        "MG_52\tMG_52\t209.8\n"
                        "MG_53\tMG_53\t219.2"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/gebv/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for GCTA outputs. Defaults to 'gebv_result', which produces "
                        "gebv_result.hsq, gebv_result.indi.blp, and gebv_result.log."
                    ),
                },
                "top_percent": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Percentage of highest-GEBV individuals to export. Defaults to 10.",
                },
            },
            "required": ["grm_prefix", "pheno"],
        }

    async def execute(
        self,
        grm_prefix: str,
        pheno: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        top_percent: int = 10,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                grm_prefix=grm_prefix,
                pheno=pheno,
                output_dir=output_dir,
                prefix=prefix,
                top_percent=top_percent,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: GEBV analysis failed.\n"
                f"- Input GRM prefix: {prepared.grm_prefix_path}\n"
                f"- Input phenotype: {prepared.pheno_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "GEBV analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input GRM prefix: {prepared.grm_prefix_path}",
            f"- Input phenotype: {prepared.pheno_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- GCTA hsq file: {prepared.hsq_path}",
            f"- GCTA BLP file: {prepared.blp_path}",
            f"- GCTA log: {prepared.log_path}",
            f"- Clean GEBV file: {prepared.clean_path}",
            f"- Top-{prepared.top_percent}% file: {prepared.top_path}",
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
        grm_prefix: str,
        pheno: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        top_percent: int = 10,
    ) -> PreparedGebvRun:
        grm_prefix_path = self._resolve_grm_prefix(grm_prefix)
        pheno_path = self._resolve_pheno(pheno)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "gebv_result")
        top_percent_value = self._validate_top_percent(top_percent)

        output_prefix_path = output_root / prefix_name
        hsq_path = output_prefix_path.with_suffix(".hsq")
        blp_path = output_prefix_path.with_suffix(".indi.blp")
        log_path = output_prefix_path.with_suffix(".log")
        clean_path = output_root / self._clean_filename(prefix_name)
        top_path = output_root / self._top_filename(prefix_name, top_percent_value)
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["gcta64", "python3"])
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
            "--grm-prefix",
            str(grm_prefix_path),
            "--pheno",
            str(pheno_path),
            "--out-prefix",
            str(output_prefix_path),
            "--clean-output",
            str(clean_path),
            "--top-output",
            str(top_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--top-percent",
            str(top_percent_value),
        ]

        return PreparedGebvRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            grm_prefix_path=grm_prefix_path,
            pheno_path=pheno_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            hsq_path=hsq_path,
            blp_path=blp_path,
            log_path=log_path,
            clean_path=clean_path,
            top_path=top_path,
            summary_path=summary_path,
            top_percent=top_percent_value,
        )

    def _resolve_grm_prefix(self, grm_prefix: str) -> Path:
        prefix_path = _resolve_path(grm_prefix, self.allowed_dir)
        required = [prefix_path.with_suffix(ext) for ext in (".grm.bin", ".grm.N.bin", ".grm.id")]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ValueError(f"GRM prefix is missing required files: {', '.join(missing)}")
        return prefix_path

    def _resolve_pheno(self, pheno: str) -> Path:
        pheno_path = _resolve_path(pheno, self.allowed_dir)
        if not pheno_path.exists():
            raise ValueError(f"Phenotype file not found: {pheno_path}")
        if not pheno_path.is_file():
            raise ValueError(f"Phenotype input must be a file: {pheno_path}")
        return pheno_path

    def _validate_top_percent(self, top_percent: int) -> int:
        if not isinstance(top_percent, int):
            raise ValueError("top_percent must be an integer between 1 and 100")
        if top_percent < 1 or top_percent > 100:
            raise ValueError("top_percent must be between 1 and 100")
        return top_percent

    def _clean_filename(self, prefix_name: str) -> str:
        if prefix_name == "gebv_result":
            return "gebv_clean.txt"
        return f"{prefix_name}_clean.txt"

    def _top_filename(self, prefix_name: str, top_percent: int) -> str:
        if prefix_name == "gebv_result":
            return f"breeding_analysis_top_{top_percent}percent.txt"
        return f"{prefix_name}_top_{top_percent}percent.txt"
