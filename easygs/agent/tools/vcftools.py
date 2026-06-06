"""Generic vcftools analysis runner."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase
MANAGED_VCFTOOLS_FLAGS = {"--vcf", "--gzvcf", "--out"}


@dataclass
class PreparedVcftoolsRun:
    """Prepared generic vcftools execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    vcftools_args: list[str]
    output_dir: Path
    output_prefix_path: Path
    log_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "vcftools_args": list(self.vcftools_args),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "log_path": str(self.log_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunVcftoolsTool(PlinkToolBase, Tool):
    """Run any vcftools-supported operation with EasyGS-managed input/output paths."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="vcftools_analysis",
            default_output_subdir="vcftools",
        )
        self.script_path = self.skill_dir / "vcftools_runner.py"

    @property
    def name(self) -> str:
        return "run_vcftools"

    @property
    def description(self) -> str:
        return (
            "Run vcftools with structured argument tokens. EasyGS manages --vcf/--gzvcf "
            "and --out, while args carries the vcftools operation/options requested by the user."
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
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "vcftools argument tokens, excluding EasyGS-managed --vcf, --gzvcf, and --out. "
                        "For example ['--freq'] or ['--maf', '0.05', '--recode', '--recode-INFO-all']."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/vcftools/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": "Basename for vcftools outputs. Defaults to 'vcftools'.",
                },
            },
            "required": ["vcf", "args"],
        }

    async def execute(
        self,
        vcf: str,
        args: list[str],
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                args=args,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: vcftools run failed.\n"
                f"- VCF: {prepared.vcf_path}\n"
                f"- Args: {' '.join(prepared.vcftools_args)}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        output_files = self._collect_output_files(prepared.output_prefix_path, prepared.summary_path)
        lines = [
            "vcftools run completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Args: {' '.join(prepared.vcftools_args)}",
            f"- Output dir: {prepared.output_dir}",
            f"- Output prefix: {prepared.output_prefix_path}",
            f"- vcftools log: {prepared.log_path}",
            f"- Summary file: {prepared.summary_path}",
        ]
        if output_files:
            lines.extend(f"- Output file: {path}" for path in output_files)
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
        args: list[str],
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedVcftoolsRun:
        vcf_path = self._resolve_vcf(vcf)
        vcftools_args = self._normalize_vcftools_args(args)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "vcftools")
        output_prefix_path = output_root / prefix_name
        log_path = output_root / f"{prefix_name}.log"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        if not self.script_path.exists():
            raise ValueError(f"pipeline script not found: {self.script_path}")

        env_status = await self._get_environment_status(["vcftools", "python3"])
        if env_status["error"]:
            error = env_status["error"]
            raise ValueError(error[7:] if error.startswith("Error: ") else error)

        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "python3",
            str(self.script_path),
            "--vcf",
            str(vcf_path),
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--args-json",
            json.dumps(vcftools_args, ensure_ascii=False),
        ]

        return PreparedVcftoolsRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            vcftools_args=vcftools_args,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            log_path=log_path,
            summary_path=summary_path,
        )

    def _normalize_vcftools_args(self, args: list[str]) -> list[str]:
        if not isinstance(args, list) or not args:
            raise ValueError("args must be a non-empty array of vcftools argument tokens.")
        tokens = [str(item).strip() for item in args]
        if any(not token for token in tokens):
            raise ValueError("args must not contain empty tokens.")
        if tokens and tokens[0] == "vcftools":
            raise ValueError("args must contain only vcftools option tokens, not the 'vcftools' command.")
        forbidden = [token for token in tokens if self._is_managed_flag_token(token)]
        if forbidden:
            joined = ", ".join(forbidden)
            raise ValueError(f"Do not include EasyGS-managed vcftools flags in args: {joined}")
        return tokens

    def _is_managed_flag_token(self, token: str) -> bool:
        if token in MANAGED_VCFTOOLS_FLAGS:
            return True
        return any(token.startswith(f"{flag}=") for flag in MANAGED_VCFTOOLS_FLAGS)

    def _collect_output_files(self, output_prefix_path: Path, summary_path: Path) -> list[Path]:
        if not output_prefix_path.parent.exists():
            return []
        files = [
            path
            for path in output_prefix_path.parent.glob(f"{output_prefix_path.name}*")
            if path.is_file() and path.resolve() != summary_path.resolve()
        ]
        return sorted(files)
