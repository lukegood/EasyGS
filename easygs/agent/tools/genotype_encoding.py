"""PLINK additive genotype encoding tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedGenotypeEncodingRun:
    """Prepared PLINK additive genotype-encoding execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    input_label: str
    input_prefix_path: Path
    output_dir: Path
    output_prefix_path: Path
    raw_path: Path
    log_path: Path
    nosex_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "input_label": self.input_label,
            "input_prefix_path": str(self.input_prefix_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "raw_path": str(self.raw_path),
            "log_path": str(self.log_path),
            "nosex_path": str(self.nosex_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }
        if self.input_label == "ped":
            metadata["ped_prefix_path"] = str(self.input_prefix_path)
        else:
            metadata["bfile_prefix_path"] = str(self.input_prefix_path)
        return metadata



class RunGenotypeEncodingTool(PlinkToolBase, Tool):
    """Run PLINK --recodeA to create a 0/1/2 additive genotype matrix."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="genotype_encoding_analysis",
            default_output_subdir="genotype_encoding",
        )
        self.script_path = self.skill_dir / "genotype_encoding.sh"
        self.summary_script_path = self.skill_dir / "summarize_genotype_encoding.py"

    @property
    def name(self) -> str:
        return "run_genotype_encoding"

    @property
    def description(self) -> str:
        return (
            "Run PLINK --recodeA in the EasyGS_2 environment to encode genotypes as "
            "0/1/2 additive dosage. Provide exactly one user-supplied input prefix: "
            "ped_prefix for PED/MAP input or bfile_prefix for BED/BIM/FAM input. "
            "Example data prefix: /home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ped_prefix": {
                    "type": "string",
                    "description": (
                        "PLINK PED/MAP input prefix. Provide the prefix path without .ped/.map, "
                        "for example /home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter. "
                        "Use exactly one of ped_prefix or bfile_prefix."
                    ),
                },
                "bfile_prefix": {
                    "type": "string",
                    "description": (
                        "PLINK binary BED/BIM/FAM input prefix. Provide the prefix path without "
                        ".bed/.bim/.fam, for example /home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter. "
                        "Use exactly one of ped_prefix or bfile_prefix."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/genotype_encoding/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for PLINK outputs. Defaults to 'filter'. Generates "
                        "<prefix>.raw, <prefix>.log, and optionally <prefix>.nosex."
                    ),
                },
            },
        }

    async def execute(
        self,
        ped_prefix: str | None = None,
        bfile_prefix: str | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                ped_prefix=ped_prefix,
                bfile_prefix=bfile_prefix,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Genotype encoding failed.\n"
                f"- Input ({prepared.input_label}): {prepared.input_prefix_path}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Genotype encoding completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input ({prepared.input_label}): {prepared.input_prefix_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Additive genotype matrix: {prepared.raw_path}",
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
        ped_prefix: str | None = None,
        bfile_prefix: str | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedGenotypeEncodingRun:
        inputs_provided = [value is not None for value in (ped_prefix, bfile_prefix)]
        if sum(inputs_provided) != 1:
            raise ValueError(
                "Provide exactly one of ped_prefix or bfile_prefix. "
                "Example prefix: /home/wlg/easyGP/work/1.QC/4.格式转换与预处理/filter"
            )

        if ped_prefix is not None:
            input_label = "ped"
            input_prefix_path = self._resolve_ped_prefix(ped_prefix)
        else:
            input_label = "bfile"
            input_prefix_path = self._resolve_bfile_prefix(str(bfile_prefix))

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, "filter")
        output_prefix_path = output_root / prefix_name
        raw_path = output_root / f"{prefix_name}.raw"
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
            "--out-prefix",
            str(output_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]
        if input_label == "ped":
            command.extend(["--ped-prefix", str(input_prefix_path)])
        else:
            command.extend(["--bfile", str(input_prefix_path)])

        return PreparedGenotypeEncodingRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            input_label=input_label,
            input_prefix_path=input_prefix_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            raw_path=raw_path,
            log_path=log_path,
            nosex_path=nosex_path,
            summary_path=summary_path,
        )
