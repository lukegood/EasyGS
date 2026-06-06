"""VCF basic statistics tool backed by bundled bcftools commands."""

import asyncio
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path

@dataclass
class PreparedVcfStatsRun:
    """Prepared VCF statistics execution plan."""

    launcher: str
    label: str
    command: list[str]
    vcf_path: Path
    stats_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        """Convert the prepared run into JSON-safe metadata."""
        return {
            "launcher": self.launcher,
            "label": self.label,
            "vcf_path": str(self.vcf_path),
            "stats_path": str(self.stats_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunVcfStatsTool(Tool):
    """Tool to run bundled bcftools-based VCF statistics."""

    def __init__(
        self,
        workspace: Path,
        restrict_to_workspace: bool = False,
        timeout: int = 1800,
    ):
        self.workspace = workspace
        self.timeout = timeout
        self.allowed_dir = workspace if restrict_to_workspace else None
        self.script_path = (
            Path(__file__).resolve().parents[2]
            / "skills"
            / "vcf_stats"
            / "scripts"
            / "vcf_stats.sh"
        )
        self.env_name = "EasyGS_1"

    @property
    def name(self) -> str:
        return "run_vcf_stats"

    @property
    def description(self) -> str:
        return (
            "Run bcftools stats for a VCF/VCF.GZ file and extract key summary lines "
            "into cal.txt-style output. The tool validates the EasyGS_1 environment first."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {
                    "type": "string",
                    "description": "User-provided path to the input VCF or VCF.GZ file.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional directory for default outputs. If omitted, outputs are "
                        "written to workspace/default_results/vcf_stats/ as vcf_stats.txt and cal.txt."
                    ),
                },
                "stats_output": {
                    "type": "string",
                    "description": "Optional explicit path for the raw bcftools stats output file.",
                },
                "summary_output": {
                    "type": "string",
                    "description": "Optional explicit path for the extracted summary output file.",
                },
            },
            "required": ["vcf"],
        }

    async def execute(
        self,
        vcf: str,
        output_dir: str | None = None,
        stats_output: str | None = None,
        summary_output: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                output_dir=output_dir,
                stats_output=stats_output,
                summary_output=summary_output,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            return self._format_run_failure(run_result=run_result, prepared=prepared)

        return self._format_run_success(
            prepared=prepared,
            stdout=run_result["stdout"],
            stderr=run_result["stderr"],
        )

    async def prepare_run(
        self,
        *,
        vcf: str,
        output_dir: str | None = None,
        stats_output: str | None = None,
        summary_output: str | None = None,
    ) -> PreparedVcfStatsRun:
        """Resolve inputs and build the command for a VCF statistics run."""
        vcf_path = _resolve_path(vcf, self.allowed_dir)
        stats_path, summary_path = self._resolve_output_paths(
            output_dir=output_dir,
            stats_output=stats_output,
            summary_output=summary_output,
        )

        for label, path in {
            "VCF": vcf_path,
            "pipeline script": self.script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        if not vcf_path.is_file():
            raise ValueError(f"VCF input must be a file: {vcf_path}")

        if not (str(vcf_path).endswith(".vcf") or str(vcf_path).endswith(".vcf.gz")):
            raise ValueError(f"VCF input must end with .vcf or .vcf.gz: {vcf_path}")

        if stats_path == summary_path:
            raise ValueError("stats_output and summary_output must be different files")

        env_status = await self._get_environment_status()
        if env_status["error"]:
            raise ValueError(env_status["error"][7:] if env_status["error"].startswith("Error: ") else env_status["error"])

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "bash",
            str(self.script_path),
            "--vcf",
            str(vcf_path),
            "--stats-output",
            str(stats_path),
            "--summary-output",
            str(summary_path),
        ]

        return PreparedVcfStatsRun(
            launcher=env_status["launcher"],
            label=self._build_label(vcf_path),
            command=command,
            vcf_path=vcf_path,
            stats_path=stats_path,
            summary_path=summary_path,
        )

    def _resolve_output_paths(
        self,
        output_dir: str | None,
        stats_output: str | None,
        summary_output: str | None,
    ) -> tuple[Path, Path]:
        if output_dir:
            root = _resolve_path(output_dir, self.allowed_dir)
            stats_path = _resolve_path(stats_output, self.allowed_dir) if stats_output else root / "vcf_stats.txt"
            summary_path = _resolve_path(summary_output, self.allowed_dir) if summary_output else root / "cal.txt"
            return stats_path, summary_path

        if stats_output or summary_output:
            if not (stats_output and summary_output):
                raise ValueError("Provide output_dir or both stats_output and summary_output")
            return (
                _resolve_path(stats_output, self.allowed_dir),
                _resolve_path(summary_output, self.allowed_dir),
            )

        default_root = self.workspace / "default_results" / "vcf_stats"
        return default_root / "vcf_stats.txt", default_root / "cal.txt"

    async def _get_environment_status(self) -> dict[str, str]:
        launchers = self._find_launchers()
        if not launchers:
            return {
                "launcher": "",
                "error": "Error: Neither 'mamba' nor 'conda' is available on PATH.",
            }

        env_missing_error = ""
        launcher_errors: list[str] = []
        for launcher in launchers:
            env_list = await self._run_command([launcher, "env", "list"], timeout=30)
            if env_list["returncode"] != 0:
                details = self._join_output(env_list["stdout"], env_list["stderr"])
                launcher_errors.append(f"{launcher}: {details or 'failed to inspect environments'}")
                continue

            if not re.search(rf"(?m)^\s*{re.escape(self.env_name)}(?:\s|$)", env_list["stdout"]):
                env_missing_error = (
                    f"Error: Required environment '{self.env_name}' was not found. "
                    "Create or activate it before running VCF statistics."
                )
                continue

            tool_check = await self._run_command(
                [
                    launcher,
                    "run",
                    "-n",
                    self.env_name,
                    "bash",
                    "-c",
                    "command -v bcftools >/dev/null",
                ],
                timeout=60,
            )
            if tool_check["returncode"] == 0:
                return {"launcher": launcher, "error": ""}

            details = self._join_output(tool_check["stdout"], tool_check["stderr"])
            launcher_errors.append(f"{launcher}: {details or 'missing required executables'}")

        if env_missing_error:
            return {"launcher": "", "error": env_missing_error}

        detail_block = "\n".join(f"- {item}" for item in launcher_errors)
        return {
            "launcher": "",
            "error": (
                "Error: Environment 'EasyGS_1' is present but the launcher checks failed.\n"
                f"{detail_block}"
            ).strip(),
        }

    def _find_launchers(self) -> list[str]:
        launchers: list[str] = []
        for candidate in ("conda", "mamba"):
            resolved = shutil.which(candidate)
            if resolved and resolved not in launchers:
                launchers.append(resolved)

        home = Path.home()
        fallback_paths = [
            home / "miniforge3" / "condabin" / "conda",
            home / "miniforge3" / "bin" / "conda",
            home / "miniforge3" / "condabin" / "mamba",
            home / "miniforge3" / "bin" / "mamba",
            home / "miniconda3" / "bin" / "conda",
            home / "miniconda3" / "bin" / "mamba",
            home / "anaconda3" / "bin" / "conda",
            home / "anaconda3" / "bin" / "mamba",
        ]
        for path in fallback_paths:
            if path.exists() and str(path) not in launchers:
                launchers.append(str(path))
        return launchers

    async def _run_command(self, command: list[str], timeout: int) -> dict[str, str | int]:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": 124,
            }
        return {
            "stdout": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
            "returncode": process.returncode,
        }

    def _build_label(self, vcf_path: Path) -> str:
        if vcf_path.name.endswith(".vcf.gz"):
            return vcf_path.name[:-7]
        if vcf_path.name.endswith(".vcf"):
            return vcf_path.stem
        return vcf_path.name

    def _format_run_failure(self, run_result: dict[str, str | int], prepared: PreparedVcfStatsRun) -> str:
        details = self._join_output(run_result["stdout"], run_result["stderr"])
        return (
            "Error: VCF statistics analysis failed.\n"
            "Resolved inputs:\n"
            f"- VCF: {prepared.vcf_path}\n"
            "Resolved outputs:\n"
            f"- Raw stats file: {prepared.stats_path}\n"
            f"- Extracted summary file: {prepared.summary_path}\n"
            f"Exit code: {run_result['returncode']}\n"
            f"{details}"
        ).strip()

    def _format_run_success(
        self,
        prepared: PreparedVcfStatsRun,
        stdout: str,
        stderr: str,
    ) -> str:
        lines = [
            "VCF basic statistics completed.",
            f"- Launcher: {prepared.launcher}",
            f"- VCF: {prepared.vcf_path}",
            f"- Raw stats file: {prepared.stats_path}",
            f"- Extracted summary file: {prepared.summary_path}",
        ]
        if prepared.notes:
            lines.extend(f"- Note: {note}" for note in prepared.notes)

        preview = self._read_preview(prepared.summary_path)
        if preview:
            lines.append("")
            lines.append("Summary preview:")
            lines.append(preview)

        details = self._join_output(stdout, stderr)
        if details:
            lines.append("")
            lines.append(details)
        return "\n".join(lines)

    def _read_preview(self, path: Path, max_lines: int = 20, max_chars: int = 4000) -> str:
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if not content:
            return ""
        lines = content.splitlines()[:max_lines]
        preview = "\n".join(lines)
        return preview[:max_chars].strip()

    def _join_output(self, stdout: Any, stderr: Any) -> str:
        parts: list[str] = []
        if isinstance(stdout, str) and stdout.strip():
            parts.append(stdout.strip())
        if isinstance(stderr, str) and stderr.strip():
            parts.append(f"STDERR:\n{stderr.strip()}")
        return "\n".join(parts).strip()
