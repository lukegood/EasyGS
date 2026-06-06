"""ADMIXTURE population-structure analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedAdmixtureRun:
    """Prepared ADMIXTURE execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    bfile_prefix_path: Path
    output_dir: Path
    dataset_prefix_path: Path
    summary_path: Path
    best_k_result_path: Path
    k_min: int
    k_max: int
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "output_dir": str(self.output_dir),
            "dataset_prefix_path": str(self.dataset_prefix_path),
            "summary_path": str(self.summary_path),
            "best_k_result_path": str(self.best_k_result_path),
            "k_min": self.k_min,
            "k_max": self.k_max,
            "notes": list(self.notes),
        }



class RunAdmixtureTool(PlinkToolBase, Tool):
    """Run ADMIXTURE across a K range and pick the best CV error."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 7200):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="admixture_analysis",
            default_output_subdir="admixture",
        )
        self.script_path = self.skill_dir / "admixture.sh"
        self.summary_script_path = self.skill_dir / "summarize_admixture.py"

    @property
    def name(self) -> str:
        return "run_admixture"

    @property
    def description(self) -> str:
        return (
            "Run ADMIXTURE with cross-validation across a range of K values on a BFILE "
            "dataset and summarize the best K using the EasyGS_2 environment."
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
                "k_min": {
                    "type": "integer",
                    "description": "Minimum K value for ADMIXTURE. Defaults to 2.",
                },
                "k_max": {
                    "type": "integer",
                    "description": "Maximum K value for ADMIXTURE. Defaults to 10.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/admixture/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Dataset basename used inside the output directory for ADMIXTURE .Q/.P "
                        "files. Defaults to the basename of the input BFILE."
                    ),
                },
            },
            "required": ["bfile_prefix"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        k_min: int = 2,
        k_max: int = 10,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                k_min=k_min,
                k_max=k_max,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: ADMIXTURE analysis failed.\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- K range: {prepared.k_min}-{prepared.k_max}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "ADMIXTURE analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- K range: {prepared.k_min}-{prepared.k_max}",
            f"- Output dir: {prepared.output_dir}",
            f"- Dataset prefix: {prepared.dataset_prefix_path}",
            f"- Best K result: {prepared.best_k_result_path}",
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
        k_min: int = 2,
        k_max: int = 10,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedAdmixtureRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        try:
            k_min_value = int(k_min)
            k_max_value = int(k_max)
        except (TypeError, ValueError) as exc:
            raise ValueError("k_min and k_max must be integers.") from exc
        if k_min_value < 2:
            raise ValueError("k_min must be at least 2.")
        if k_max_value < k_min_value:
            raise ValueError("k_max must be greater than or equal to k_min.")

        output_root = self._resolve_output_dir(output_dir)
        default_prefix = bfile_prefix_path.name
        prefix_name = self._normalize_prefix_name(prefix, default_prefix)
        dataset_prefix_path = output_root / prefix_name
        best_k_result_path = output_root / "best_k_result.txt"
        summary_path = output_root / f"{prefix_name}_admixture_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["admixture", "python3"])
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
            "--dataset-prefix",
            prefix_name,
            "--output-dir",
            str(output_root),
            "--k-min",
            str(k_min_value),
            "--k-max",
            str(k_max_value),
            "--best-k-output",
            str(best_k_result_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedAdmixtureRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            output_dir=output_root,
            dataset_prefix_path=dataset_prefix_path,
            summary_path=summary_path,
            best_k_result_path=best_k_result_path,
            k_min=k_min_value,
            k_max=k_max_value,
        )
