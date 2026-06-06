"""Shared helpers for PLINK-based analysis tools."""

import asyncio
import re
import shlex
import shutil
from pathlib import Path
from typing import Any

from easygs.agent.tools.filesystem import _resolve_path


class PlinkToolBase:
    """Shared environment validation and command helpers for PLINK-based tools."""

    def __init__(
        self,
        workspace: Path,
        restrict_to_workspace: bool,
        timeout: int,
        *,
        skill_name: str,
        default_output_subdir: str,
        env_name: str = "EasyGS_2",
    ):
        self.workspace = workspace
        self.timeout = timeout
        self.allowed_dir = workspace if restrict_to_workspace else None
        self.env_name = env_name
        self.skill_dir = Path(__file__).resolve().parents[2] / "skills" / skill_name / "scripts"
        self.default_output_subdir = Path(default_output_subdir)

    def _default_output_dir(self) -> Path:
        return self.workspace / "default_results" / self.default_output_subdir

    def _resolve_output_dir(self, output_dir: str | None) -> Path:
        if output_dir:
            return _resolve_path(output_dir, self.allowed_dir)
        return self._default_output_dir()

    def _resolve_vcf(self, vcf: str) -> Path:
        vcf_path = _resolve_path(vcf, self.allowed_dir)
        if not vcf_path.exists():
            raise ValueError(f"VCF not found: {vcf_path}")
        if not vcf_path.is_file():
            raise ValueError(f"VCF input must be a file: {vcf_path}")
        if not (str(vcf_path).endswith(".vcf") or str(vcf_path).endswith(".vcf.gz")):
            raise ValueError(f"VCF input must end with .vcf or .vcf.gz: {vcf_path}")
        return vcf_path

    def _resolve_bfile_prefix(self, bfile_prefix: str) -> Path:
        prefix_path = _resolve_path(bfile_prefix, self.allowed_dir)
        required = [prefix_path.with_suffix(ext) for ext in (".bed", ".bim", ".fam")]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ValueError(f"BFILE prefix is missing required files: {', '.join(missing)}")
        return prefix_path

    def _resolve_ped_prefix(self, ped_prefix: str) -> Path:
        prefix_path = _resolve_path(ped_prefix, self.allowed_dir)
        required = [prefix_path.with_suffix(ext) for ext in (".ped", ".map")]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ValueError(f"PED prefix is missing required files: {', '.join(missing)}")
        return prefix_path

    def _normalize_prefix_name(self, value: str | None, default: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            return default
        if candidate.endswith(".vcf.gz"):
            candidate = candidate[: -len(".vcf.gz")]
        elif candidate.endswith(".vcf"):
            candidate = candidate[: -len(".vcf")]
        candidate = candidate.rstrip(".")
        return candidate or default

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

    async def _get_environment_status(self, required_tools: list[str]) -> dict[str, str]:
        launchers = self._find_launchers()
        if not launchers:
            return {"launcher": "", "error": "Error: Neither 'mamba' nor 'conda' is available on PATH."}

        env_missing_error = ""
        launcher_errors: list[str] = []
        check_cmd = " && ".join(f"command -v {shlex.quote(tool)} >/dev/null" for tool in required_tools)

        for launcher in launchers:
            env_list = await self._run_command([launcher, "env", "list"], timeout=30)
            if env_list["returncode"] != 0:
                details = self._join_output(env_list["stdout"], env_list["stderr"])
                launcher_errors.append(f"{launcher}: {details or 'failed to inspect environments'}")
                continue

            if not re.search(rf"(?m)^\s*{re.escape(self.env_name)}(?:\s|$)", str(env_list["stdout"])):
                env_missing_error = (
                    f"Error: Required environment '{self.env_name}' was not found. "
                    "Create or activate it before running PLINK analysis."
                )
                continue

            tool_check = await self._run_command(
                [launcher, "run", "-n", self.env_name, "bash", "-c", check_cmd],
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
                f"Error: Environment '{self.env_name}' is present but the launcher checks failed.\n"
                f"{detail_block}"
            ).strip(),
        }

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
            return {"stdout": "", "stderr": f"Command timed out after {timeout} seconds", "returncode": 124}
        return {
            "stdout": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
            "returncode": process.returncode,
        }

    def _join_output(self, stdout: Any, stderr: Any) -> str:
        parts: list[str] = []
        if isinstance(stdout, str) and stdout.strip():
            parts.append(stdout.strip())
        if isinstance(stderr, str) and stderr.strip():
            parts.append(f"STDERR:\n{stderr.strip()}")
        return "\n".join(parts).strip()

    def _read_preview(self, path: Path, max_lines: int = 20, max_chars: int = 4000) -> str:
        if not path.exists():
            return ""
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if not content:
            return ""
        return "\n".join(content.splitlines()[:max_lines])[:max_chars].strip()
