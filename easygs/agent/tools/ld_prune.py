"""PLINK-based LD-pruning tools."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedLdPruneRun:
    """Prepared LD-pruning execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    input_label: str
    input_path: Path
    output_dir: Path
    output_prefix: Path
    prune_in_path: Path
    prune_out_path: Path
    summary_path: Path
    window_size: int
    step_size: int
    r2_threshold: float
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "input_label": self.input_label,
            "input_path": str(self.input_path),
            "output_dir": str(self.output_dir),
            "output_prefix": str(self.output_prefix),
            "prune_in_path": str(self.prune_in_path),
            "prune_out_path": str(self.prune_out_path),
            "summary_path": str(self.summary_path),
            "window_size": self.window_size,
            "step_size": self.step_size,
            "r2_threshold": self.r2_threshold,
            "notes": list(self.notes),
        }



class RunLdPruneTool(PlinkToolBase, Tool):
    """Run PLINK LD pruning on a VCF or PLINK BED dataset."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="ld_prune_analysis",
            default_output_subdir="ld_prune",
        )
        self.script_path = self.skill_dir / "ld_prune.sh"
        self.summary_script_path = self.skill_dir / "summarize_ld_prune.py"

    @property
    def name(self) -> str:
        return "run_ld_prune"

    @property
    def description(self) -> str:
        return (
            "Run PLINK LD pruning from either a VCF/VCF.GZ input or a PLINK bfile prefix, "
            "and summarize retained versus pruned variants using the EasyGS_2 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {"type": "string", "description": "Optional input VCF or VCF.GZ path."},
                "bfile_prefix": {"type": "string", "description": "Optional PLINK bfile prefix (without extension)."},
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/ld_prune/."
                    ),
                },
                "prefix": {"type": "string", "description": "Output prefix basename. Defaults to 'ldprune'."},
                "window_size": {"type": "integer", "description": "PLINK indep-pairwise window size. Defaults to 50."},
                "step_size": {"type": "integer", "description": "PLINK indep-pairwise step size. Defaults to 5."},
                "r2_threshold": {"type": "number", "description": "PLINK indep-pairwise r^2 threshold. Defaults to 0.2."},
            },
        }

    async def execute(
        self,
        vcf: str | None = None,
        bfile_prefix: str | None = None,
        output_dir: str | None = None,
        prefix: str = "ldprune",
        window_size: int = 50,
        step_size: int = 5,
        r2_threshold: float = 0.2,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                bfile_prefix=bfile_prefix,
                output_dir=output_dir,
                prefix=prefix,
                window_size=window_size,
                step_size=step_size,
                r2_threshold=r2_threshold,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: LD pruning failed.\n"
                f"- Input ({prepared.input_label}): {prepared.input_path}\n"
                f"- Output prefix: {prepared.output_prefix}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "LD pruning completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input ({prepared.input_label}): {prepared.input_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Prune-in file: {prepared.prune_in_path}",
            f"- Prune-out file: {prepared.prune_out_path}",
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
        vcf: str | None = None,
        bfile_prefix: str | None = None,
        output_dir: str | None = None,
        prefix: str = "ldprune",
        window_size: int = 50,
        step_size: int = 5,
        r2_threshold: float = 0.2,
    ) -> PreparedLdPruneRun:
        if bool(vcf) == bool(bfile_prefix):
            raise ValueError("Provide exactly one of vcf or bfile_prefix")

        output_root = self._resolve_output_dir(output_dir)
        output_prefix = output_root / (prefix or "ldprune")
        summary_path = output_root / f"{output_prefix.name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        if vcf:
            input_label = "vcf"
            input_path = self._resolve_vcf(vcf)
        else:
            input_label = "bfile"
            input_path = self._resolve_bfile_prefix(str(bfile_prefix))

        env_status = await self._get_environment_status(["plink"])
        if env_status["error"]:
            raise ValueError(env_status["error"][7:] if env_status["error"].startswith("Error: ") else env_status["error"])

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "bash",
            str(self.script_path),
            "--out-prefix",
            str(output_prefix),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--window-size",
            str(window_size),
            "--step-size",
            str(step_size),
            "--r2-threshold",
            str(r2_threshold),
        ]
        if input_label == "vcf":
            command.extend(["--vcf", str(input_path)])
        else:
            command.extend(["--bfile", str(input_path)])

        return PreparedLdPruneRun(
            launcher=env_status["launcher"],
            prefix=output_prefix.name,
            command=command,
            input_label=input_label,
            input_path=input_path,
            output_dir=output_root,
            output_prefix=output_prefix,
            prune_in_path=output_prefix.with_suffix(".prune.in"),
            prune_out_path=output_prefix.with_suffix(".prune.out"),
            summary_path=summary_path,
            window_size=window_size,
            step_size=step_size,
            r2_threshold=r2_threshold,
        )
