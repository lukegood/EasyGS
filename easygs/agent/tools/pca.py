"""PCA analysis tool for PLINK BFILE datasets."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedPcaRun:
    """Prepared PLINK PCA execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    bfile_prefix_path: Path
    output_dir: Path
    output_prefix_path: Path
    eigenval_path: Path
    eigenvec_path: Path
    log_path: Path
    summary_path: Path
    components: int
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "eigenval_path": str(self.eigenval_path),
            "eigenvec_path": str(self.eigenvec_path),
            "log_path": str(self.log_path),
            "summary_path": str(self.summary_path),
            "components": self.components,
            "notes": list(self.notes),
        }



class RunPcaTool(PlinkToolBase, Tool):
    """Run PLINK PCA on a BFILE dataset and generate a variance summary."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="pca_analysis",
            default_output_subdir="pca",
        )
        self.script_path = self.skill_dir / "pca.sh"
        self.summary_script_path = self.skill_dir / "summarize_pca.py"

    @property
    def name(self) -> str:
        return "run_pca"

    @property
    def description(self) -> str:
        return (
            "Run PLINK PCA on a PLINK BFILE dataset and summarize the explained variance "
            "for each principal component using the EasyGS_2 environment."
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
                "components": {
                    "type": "integer",
                    "description": "Number of principal components to compute. Defaults to 20.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/pca/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for PCA outputs. Defaults to 'data_pca_pruned'."
                    ),
                },
            },
            "required": ["bfile_prefix"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        components: int = 20,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                components=components,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: PCA analysis failed.\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- Components: {prepared.components}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "PCA analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- Components: {prepared.components}",
            f"- Output dir: {prepared.output_dir}",
            f"- Eigenvalue file: {prepared.eigenval_path}",
            f"- Eigenvector file: {prepared.eigenvec_path}",
            f"- PLINK log: {prepared.log_path}",
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
        components: int = 20,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedPcaRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        if int(components) <= 0:
            raise ValueError("components must be a positive integer.")

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "data_pca_pruned")
        output_prefix_path = output_root / prefix_name
        eigenval_path = output_prefix_path.with_suffix(".eigenval")
        eigenvec_path = output_prefix_path.with_suffix(".eigenvec")
        log_path = output_prefix_path.with_suffix(".log")
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
            "--components",
            str(int(components)),
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedPcaRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            eigenval_path=eigenval_path,
            eigenvec_path=eigenvec_path,
            log_path=log_path,
            summary_path=summary_path,
            components=int(components),
        )
