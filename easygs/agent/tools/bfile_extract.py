"""Extract variants from a PLINK BFILE into a new BFILE dataset."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedBfileExtractRun:
    """Prepared PLINK BFILE extraction execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    bfile_prefix_path: Path
    extract_path: Path
    output_dir: Path
    output_prefix_path: Path
    bed_path: Path
    bim_path: Path
    fam_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "extract_path": str(self.extract_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "bed_path": str(self.bed_path),
            "bim_path": str(self.bim_path),
            "fam_path": str(self.fam_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunBfileExtractTool(PlinkToolBase, Tool):
    """Extract a specified variant list from a PLINK BFILE and keep BED/BIM/FAM output."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="bfile_extract_analysis",
            default_output_subdir="bfile_extract",
        )
        self.script_path = self.skill_dir / "bfile_extract.sh"
        self.summary_script_path = self.skill_dir / "summarize_bfile_extract.py"

    @property
    def name(self) -> str:
        return "run_bfile_extract"

    @property
    def description(self) -> str:
        return (
            "Extract variants listed in a file from a PLINK BFILE dataset and write a new "
            "BED/BIM/FAM prefix using the EasyGS_2 environment."
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
                "extract_file": {
                    "type": "string",
                    "description": (
                        "Required path to the variant list file used by PLINK --extract, such as "
                        "data_pruned.prune.in."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/bfile_extract/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Output BFILE prefix basename. Defaults to 'data_ld_pruned'."
                    ),
                },
            },
            "required": ["bfile_prefix", "extract_file"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        extract_file: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                extract_file=extract_file,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: BFILE extraction failed.\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- Extract file: {prepared.extract_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "BFILE extraction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- Extract file: {prepared.extract_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- BED file: {prepared.bed_path}",
            f"- BIM file: {prepared.bim_path}",
            f"- FAM file: {prepared.fam_path}",
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
        extract_file: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedBfileExtractRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        extract_path = _resolve_path(extract_file, self.allowed_dir)
        if not extract_path.exists():
            raise ValueError(f"Extract file not found: {extract_path}")
        if not extract_path.is_file():
            raise ValueError(f"Extract file must be a file: {extract_path}")

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "data_ld_pruned")
        output_prefix_path = output_root / prefix_name
        bed_path = output_prefix_path.with_suffix(".bed")
        bim_path = output_prefix_path.with_suffix(".bim")
        fam_path = output_prefix_path.with_suffix(".fam")
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
            "--extract-file",
            str(extract_path),
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedBfileExtractRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            extract_path=extract_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            bed_path=bed_path,
            bim_path=bim_path,
            fam_path=fam_path,
            summary_path=summary_path,
        )
