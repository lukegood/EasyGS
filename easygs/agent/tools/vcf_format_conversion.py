"""Standalone VCF/PLINK format-conversion analysis tool."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.plink_common import PlinkToolBase

def _normalize_target_format(value: str | None, *, input_label: str) -> str:
    candidate = (value or "").strip().lower()
    if not candidate:
        return "vcf" if input_label == "bfile" else "bed"
    aliases = {
        "bed": "bed",
        "bfile": "bed",
        "bed/bim/fam": "bed",
        "bed_bim_fam": "bed",
        "ped": "ped",
        "ped/map": "ped",
        "ped_map": "ped",
        "vcf": "vcf",
    }
    if candidate in aliases:
        return aliases[candidate]
    raise ValueError(
        "Unsupported target_format. Use one of: bed, bed/bim/fam, bfile, ped, ped/map, vcf."
    )

def _default_prefix_for_conversion(input_label: str, target_format: str) -> str:
    if input_label == "vcf" and target_format in {"bed", "ped"}:
        return "filter"
    return "filter_turn"


@dataclass
class PreparedVcfFormatConversionRun:
    """Prepared VCF format-conversion execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    input_label: str
    input_path: Path
    output_dir: Path
    output_prefix_path: Path
    target_format: str
    summary_path: Path
    double_id: bool
    allow_extra_chr: bool
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "input_label": self.input_label,
            "input_path": str(self.input_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "target_format": self.target_format,
            "summary_path": str(self.summary_path),
            "double_id": self.double_id,
            "allow_extra_chr": self.allow_extra_chr,
            "notes": list(self.notes),
        }



class RunVcfFormatConversionTool(PlinkToolBase, Tool):
    """Convert between VCF, PED/MAP, and PLINK BED-family outputs."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="vcf_format_conversion_analysis",
            default_output_subdir="vcf_format_conversion",
        )
        self.script_path = self.skill_dir / "vcf_format_conversion.sh"
        self.summary_script_path = self.skill_dir / "summarize_conversion.py"

    @property
    def name(self) -> str:
        return "run_vcf_format_conversion"

    @property
    def description(self) -> str:
        return (
            "Convert between VCF/VCF.GZ input, PED/MAP input, and PLINK BED/BIM/FAM, PED/MAP, or exported VCF outputs "
            "using the EasyGS_2 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {"type": "string", "description": "Optional path to the input VCF or VCF.GZ file."},
                "bfile_prefix": {
                    "type": "string",
                    "description": "Optional PLINK binary prefix for input BED/BIM/FAM files.",
                },
                "ped_prefix": {
                    "type": "string",
                    "description": "Optional PLINK PED/MAP prefix for input .ped and .map files.",
                },
                "target_format": {
                    "type": "string",
                    "description": (
                        "Target output family. Supported values include 'bed' (BED/BIM/FAM), "
                        "'ped' (PED/MAP), and 'vcf'. Defaults depend on the input source."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/vcf_format_conversion/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for converted output files. Defaults to 'filter' for BED/PED "
                        "outputs from VCF input, and 'filter_turn' for exported conversions."
                    ),
                },
                "double_id": {
                    "type": "boolean",
                    "description": (
                        "Whether to add PLINK --double-id. Defaults to true for BED output "
                        "and false otherwise."
                    ),
                },
                "allow_extra_chr": {
                    "type": "boolean",
                    "description": (
                        "Whether to add PLINK --allow-extra-chr. Defaults to true for PED "
                        "output and false otherwise."
                    ),
                },
            },
        }

    async def execute(
        self,
        vcf: str | None = None,
        bfile_prefix: str | None = None,
        ped_prefix: str | None = None,
        target_format: str | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
        double_id: bool | None = None,
        allow_extra_chr: bool | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                bfile_prefix=bfile_prefix,
                ped_prefix=ped_prefix,
                target_format=target_format,
                output_dir=output_dir,
                prefix=prefix,
                double_id=double_id,
                allow_extra_chr=allow_extra_chr,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: VCF format conversion failed.\n"
                f"- Input ({prepared.input_label}): {prepared.input_path}\n"
                f"- Target format: {prepared.target_format}\n"
                f"- Output prefix: {prepared.output_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "VCF format conversion completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input ({prepared.input_label}): {prepared.input_path}",
            f"- Target format: {prepared.target_format}",
            f"- Output dir: {prepared.output_dir}",
            f"- Output prefix: {prepared.output_prefix_path}",
        ]
        prefix = str(prepared.output_prefix_path)
        if prepared.target_format == "bed":
            lines.extend(
                [
                    f"- BED file: {prefix}.bed",
                    f"- BIM file: {prefix}.bim",
                    f"- FAM file: {prefix}.fam",
                ]
            )
        elif prepared.target_format == "ped":
            lines.extend(
                [
                    f"- PED file: {prefix}.ped",
                    f"- MAP file: {prefix}.map",
                ]
            )
        elif prepared.target_format == "vcf":
            lines.append(f"- Exported VCF: {prefix}.vcf")
        lines.append(f"- Summary file: {prepared.summary_path}")
        if prepared.notes:
            lines.extend(f"- Note: {note}" for note in prepared.notes)
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
        ped_prefix: str | None = None,
        target_format: str | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
        double_id: bool | None = None,
        allow_extra_chr: bool | None = None,
    ) -> PreparedVcfFormatConversionRun:
        inputs_provided = [value is not None for value in (vcf, bfile_prefix, ped_prefix)]
        if sum(inputs_provided) != 1:
            raise ValueError("Provide exactly one of vcf, bfile_prefix, or ped_prefix")

        if vcf is not None:
            input_label = "vcf"
            input_path = self._resolve_vcf(vcf)
        elif bfile_prefix is not None:
            input_label = "bfile"
            input_path = self._resolve_bfile_prefix(str(bfile_prefix))
        else:
            input_label = "ped"
            input_path = self._resolve_ped_prefix(str(ped_prefix))

        resolved_target_format = _normalize_target_format(target_format, input_label=input_label)
        if resolved_target_format == "ped" and input_label != "vcf":
            raise ValueError(
                "PED/MAP export currently requires a VCF input. Provide vcf=... for target_format='ped'."
            )
        if resolved_target_format == "vcf" and input_label != "bfile":
            raise ValueError(
                "VCF export requires a PLINK bfile prefix. Provide bfile_prefix=... for target_format='vcf'."
            )
        if resolved_target_format == "bed" and input_label not in {"vcf", "ped"}:
            raise ValueError(
                "BED/BIM/FAM output requires VCF input or PED/MAP input. "
                "Provide vcf=... or ped_prefix=... for target_format='bed'."
            )

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(
            prefix,
            _default_prefix_for_conversion(input_label, resolved_target_format),
        )
        output_prefix_path = output_root / prefix_name
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        resolved_double_id = double_id if double_id is not None else resolved_target_format == "bed"
        resolved_allow_extra_chr = (
            allow_extra_chr if allow_extra_chr is not None else resolved_target_format == "ped"
        )

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
            "--target-format",
            resolved_target_format,
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
            "--double-id",
            "1" if resolved_double_id else "0",
            "--allow-extra-chr",
            "1" if resolved_allow_extra_chr else "0",
        ]
        if input_label == "vcf":
            command.extend(["--vcf", str(input_path)])
        elif input_label == "bfile":
            command.extend(["--bfile", str(input_path)])
        else:
            command.extend(["--ped-prefix", str(input_path)])

        notes: list[str] = []
        if resolved_target_format == "bed" and not resolved_double_id:
            notes.append("BED conversion is running without --double-id.")
        if resolved_target_format == "ped" and not resolved_allow_extra_chr:
            notes.append("PED conversion is running without --allow-extra-chr.")
        if resolved_target_format == "vcf":
            if double_id is not None:
                notes.append("--double-id is ignored for BFILE-to-VCF export.")
            if allow_extra_chr is not None:
                notes.append("--allow-extra-chr is ignored for BFILE-to-VCF export.")
        if resolved_target_format == "bed" and input_label == "ped":
            if double_id is not None:
                notes.append("--double-id is ignored for PED-to-BED conversion.")
            if allow_extra_chr is not None:
                notes.append("--allow-extra-chr is ignored for PED-to-BED conversion.")

        return PreparedVcfFormatConversionRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            input_label=input_label,
            input_path=input_path,
            output_dir=output_root,
            output_prefix_path=output_prefix_path,
            target_format=resolved_target_format,
            summary_path=summary_path,
            double_id=resolved_double_id,
            allow_extra_chr=resolved_allow_extra_chr,
            notes=notes,
        )
