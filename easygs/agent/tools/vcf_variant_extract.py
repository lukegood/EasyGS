"""VCF variant-ID subset tool backed by bcftools."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

@dataclass
class PreparedVcfVariantExtractRun:
    """Prepared execution plan for VCF variant-ID extraction."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    variant_ids_input_label: str
    normalized_variant_ids_path: Path
    output_dir: Path
    output_vcf_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "variant_ids_input_label": self.variant_ids_input_label,
            "normalized_variant_ids_path": str(self.normalized_variant_ids_path),
            "output_dir": str(self.output_dir),
            "output_vcf_path": str(self.output_vcf_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunVcfVariantExtractTool(PlinkToolBase, Tool):
    """Extract a VCF subset by variant ID list using bcftools."""

    variant_ids_format_hint = (
        "Provide one variant ID per line. Example:\n"
        "chr1.s_1067986\n"
        "chr1.s_1068121\n"
        "chr1.s_1068288\n"
        "chr1.s_1068648\n"
        "chr1.s_1068668\n"
        "chr1.s_1069042\n"
        "chr1.s_1069231\n"
        "chr1.s_1069256\n"
        "chr1.s_1069555\n"
        "chr1.s_1069916\n"
        "chr1.s_1069956\n"
        "chr1.s_1070143"
    )

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="vcf_variant_extract_analysis",
            default_output_subdir="vcf_variant_extract",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "vcf_variant_extract.sh"
        self.summary_script_path = self.skill_dir / "summarize_vcf_variant_extract.py"

    @property
    def name(self) -> str:
        return "run_vcf_variant_extract"

    @property
    def description(self) -> str:
        return (
            "Extract a subset VCF from a VCF/VCF.GZ input by variant ID list using bcftools "
            "inside the EasyGS_1 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {
                    "type": "string",
                    "description": "Input genotype file in .vcf or .vcf.gz format.",
                },
                "variant_ids": {
                    "type": "string",
                    "description": (
                        "Required variant ID list as a file path or inline text. The list should contain "
                        "one variant ID per line.\n"
                        f"{self.variant_ids_format_hint}"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/vcf_variant_extract/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for the extracted VCF and summary files. Defaults to "
                        "'<input_vcf>_id_subset'."
                    ),
                },
            },
            "required": ["vcf", "variant_ids"],
        }

    async def execute(
        self,
        vcf: str,
        variant_ids: str,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                vcf=vcf,
                variant_ids=variant_ids,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: VCF variant extraction failed.\n"
                f"- Input VCF: {prepared.vcf_path}\n"
                f"- Variant IDs input: {prepared.variant_ids_input_label}\n"
                f"- Output VCF: {prepared.output_vcf_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "VCF variant extraction completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input VCF: {prepared.vcf_path}",
            f"- Variant IDs input: {prepared.variant_ids_input_label}",
            f"- Normalized variant ID list: {prepared.normalized_variant_ids_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Extracted VCF: {prepared.output_vcf_path}",
            f"- Summary file: {prepared.summary_path}",
        ]
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
        vcf: str,
        variant_ids: str,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedVcfVariantExtractRun:
        vcf_path = self._resolve_vcf(vcf)
        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, f"{self._build_label(vcf_path)}_id_subset")
        output_vcf_path = output_root / f"{prefix_name}.vcf"
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        normalized_variant_ids_path, variant_ids_input_label, normalize_note = self._normalize_variant_ids(
            variant_ids,
            output_root,
            prefix_name,
        )

        env_status = await self._get_environment_status(["bcftools", "python3"])
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
            "--vcf",
            str(vcf_path),
            "--variant-ids",
            str(normalized_variant_ids_path),
            "--variant-ids-input-label",
            variant_ids_input_label,
            "--output-vcf",
            str(output_vcf_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        notes = [normalize_note] if normalize_note else []
        return PreparedVcfVariantExtractRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            variant_ids_input_label=variant_ids_input_label,
            normalized_variant_ids_path=normalized_variant_ids_path,
            output_dir=output_root,
            output_vcf_path=output_vcf_path,
            summary_path=summary_path,
            notes=notes,
        )

    def _normalize_variant_ids(
        self,
        variant_ids_value: str,
        output_root: Path,
        prefix_name: str,
    ) -> tuple[Path, str, str]:
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = output_root / f"{prefix_name}_variant_ids.txt"
        raw_value = variant_ids_value.strip()
        if not raw_value:
            raise ValueError(f"Variant ID list is empty.\n{self.variant_ids_format_hint}")

        if "\n" in raw_value or "\r" in raw_value:
            entries = self._parse_variant_ids_text(raw_value)
            source_label = "inline variant_ids parameter"
        else:
            candidate_path = _resolve_path(raw_value, self.allowed_dir)
            if candidate_path.exists():
                if not candidate_path.is_file():
                    raise ValueError(f"Variant ID list must be a file: {candidate_path}")
                entries = self._read_variant_ids_file(candidate_path)
                source_label = str(candidate_path)
            elif self._looks_like_path(raw_value):
                raise ValueError(f"Variant ID list not found: {candidate_path}\n{self.variant_ids_format_hint}")
            else:
                entries = self._parse_variant_ids_text(raw_value)
                source_label = "inline variant_ids parameter"

        if entries and self._looks_like_variant_id_header(entries[0]):
            entries = entries[1:]
        normalized_entries = [entry for entry in entries if entry]
        if not normalized_entries:
            raise ValueError(f"Variant ID list must contain at least one variant ID.\n{self.variant_ids_format_hint}")

        output_path.write_text("\n".join(normalized_entries) + "\n", encoding="utf-8")
        return output_path, source_label, f"Normalized variant ID list to one-ID-per-line format: {output_path}"

    def _read_variant_ids_file(self, path: Path) -> list[str]:
        suffix = path.suffix.lower()
        if suffix in {".csv", ".tsv"}:
            delimiter = "," if suffix == ".csv" else "\t"
            entries: list[str] = []
            with path.open("r", encoding="utf-8", newline="") as src:
                reader = csv.reader(src, delimiter=delimiter)
                for row in reader:
                    for cell in row:
                        stripped = cell.strip()
                        if stripped and not stripped.startswith("#"):
                            entries.append(stripped)
            return entries
        return self._parse_variant_ids_text(path.read_text(encoding="utf-8", errors="replace"))

    def _parse_variant_ids_text(self, text: str) -> list[str]:
        entries: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            entries.extend(cell.strip() for cell in re.split(r"[\s,]+", stripped) if cell.strip())
        return entries

    def _looks_like_path(self, value: str) -> bool:
        if "/" in value or "\\" in value:
            return True
        lowered = value.lower()
        return lowered.endswith((".txt", ".tsv", ".csv", ".list"))

    def _looks_like_variant_id_header(self, value: str) -> bool:
        candidate = value.strip().lower().replace("-", "_").replace(" ", "_")
        return candidate in {"id", "ids", "variant", "variant_id", "variant_ids", "marker", "marker_id", "snp", "snp_id"}

    def _build_label(self, vcf_path: Path) -> str:
        if vcf_path.name.endswith(".vcf.gz"):
            return vcf_path.name[:-7]
        if vcf_path.name.endswith(".vcf"):
            return vcf_path.stem
        return vcf_path.name
