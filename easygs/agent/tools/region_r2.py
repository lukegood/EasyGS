"""PLINK regional R2 analysis tool for BFILE datasets."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedRegionR2Run:
    """Prepared PLINK regional R2 execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    bfile_prefix_path: Path
    output_dir: Path
    output_prefix_path: Path
    ld_path: Path
    log_path: Path
    nosex_path: Path
    summary_path: Path
    chromosome: str
    from_bp: int
    to_bp: int
    ld_window: int
    ld_window_kb: int | None
    ld_window_r2: float
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "ld_path": str(self.ld_path),
            "log_path": str(self.log_path),
            "nosex_path": str(self.nosex_path),
            "summary_path": str(self.summary_path),
            "chromosome": self.chromosome,
            "from_bp": self.from_bp,
            "to_bp": self.to_bp,
            "ld_window": self.ld_window,
            "ld_window_kb": self.ld_window_kb,
            "ld_window_r2": self.ld_window_r2,
            "notes": list(self.notes),
        }



class RunRegionR2Tool(PlinkToolBase, Tool):
    """Run PLINK --r2 for a specific genomic region on a BFILE dataset."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="region_r2_analysis",
            default_output_subdir="region_r2",
        )
        self.script_path = self.skill_dir / "region_r2.sh"
        self.summary_script_path = self.skill_dir / "summarize_region_r2.py"

    @property
    def name(self) -> str:
        return "run_region_r2"

    @property
    def description(self) -> str:
        return (
            "Run PLINK pairwise R2 calculation within a specified chromosome region on a "
            "PLINK BFILE dataset and summarize the resulting .ld report."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "bfile_prefix": {
                    "type": "string",
                    "description": "PLINK binary prefix for input BED/BIM/FAM files.",
                },
                "chromosome": {
                    "type": "string",
                    "description": "Chromosome identifier passed to PLINK --chr, for example '1'.",
                },
                "from_bp": {
                    "type": "integer",
                    "description": "Start base-pair position for the region passed to PLINK --from-bp.",
                },
                "to_bp": {
                    "type": "integer",
                    "description": "End base-pair position for the region passed to PLINK --to-bp.",
                },
                "ld_window": {
                    "type": "integer",
                    "description": "Maximum number of adjacent variants considered by PLINK --ld-window. Defaults to 50.",
                },
                "ld_window_kb": {
                    "type": "integer",
                    "description": "Optional maximum distance in kb for PLINK --ld-window-kb.",
                },
                "ld_window_r2": {
                    "type": "number",
                    "description": "Minimum R2 threshold for PLINK --ld-window-r2. Defaults to 0.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/region_r2/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for PLINK outputs. Defaults to 'region_r2_limited'. Generates "
                        "<prefix>.ld, <prefix>.log, and <prefix>.nosex."
                    ),
                },
            },
            "required": ["bfile_prefix", "chromosome", "from_bp", "to_bp"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        chromosome: str,
        from_bp: int,
        to_bp: int,
        ld_window: int = 50,
        ld_window_kb: int | None = None,
        ld_window_r2: float = 0.0,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                chromosome=chromosome,
                from_bp=from_bp,
                to_bp=to_bp,
                ld_window=ld_window,
                ld_window_kb=ld_window_kb,
                ld_window_r2=ld_window_r2,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Regional R2 analysis failed.\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- Region: chr{prepared.chromosome}:{prepared.from_bp}-{prepared.to_bp}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Regional R2 analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- Region: chr{prepared.chromosome}:{prepared.from_bp}-{prepared.to_bp}",
            f"- Output dir: {prepared.output_dir}",
            f"- LD file: {prepared.ld_path}",
            f"- PLINK log: {prepared.log_path}",
            f"- PLINK .nosex: {prepared.nosex_path}",
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
        bfile_prefix: str,
        chromosome: str,
        from_bp: int,
        to_bp: int,
        ld_window: int = 50,
        ld_window_kb: int | None = None,
        ld_window_r2: float = 0.0,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedRegionR2Run:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        chromosome_value = str(chromosome).strip()
        if not chromosome_value:
            raise ValueError("chromosome must be a non-empty string.")
        if int(from_bp) < 0:
            raise ValueError("from_bp must be >= 0.")
        if int(to_bp) < 0:
            raise ValueError("to_bp must be >= 0.")
        if int(from_bp) > int(to_bp):
            raise ValueError("from_bp must be <= to_bp.")
        if int(ld_window) <= 0:
            raise ValueError("ld_window must be a positive integer.")
        if ld_window_kb is not None and int(ld_window_kb) <= 0:
            raise ValueError("ld_window_kb must be a positive integer when provided.")
        if float(ld_window_r2) < 0:
            raise ValueError("ld_window_r2 must be >= 0.")

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "region_r2_limited")
        output_prefix_path = output_root / prefix_name
        ld_path = output_root / f"{prefix_name}.ld"
        log_path = output_root / f"{prefix_name}.log"
        nosex_path = output_root / f"{prefix_name}.nosex"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["plink", "python3"])
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
            "--bfile",
            str(bfile_prefix_path),
            "--chr",
            chromosome_value,
            "--from-bp",
            str(int(from_bp)),
            "--to-bp",
            str(int(to_bp)),
            "--ld-window",
            str(int(ld_window)),
            "--ld-window-r2",
            str(float(ld_window_r2)),
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if ld_window_kb is not None:
            command.extend(["--ld-window-kb", str(int(ld_window_kb))])

        return PreparedRegionR2Run(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            ld_path=ld_path,
            log_path=log_path,
            nosex_path=nosex_path,
            summary_path=summary_path,
            chromosome=chromosome_value,
            from_bp=int(from_bp),
            to_bp=int(to_bp),
            ld_window=int(ld_window),
            ld_window_kb=int(ld_window_kb) if ld_window_kb is not None else None,
            ld_window_r2=float(ld_window_r2),
        )
