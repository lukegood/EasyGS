"""Standalone PLINK locus keep/remove analysis tool."""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

def _normalize_action(value: str | None) -> str:
    candidate = (value or "extract").strip().lower()
    aliases = {
        "extract": "extract",
        "keep": "extract",
        "retain": "extract",
        "preserve": "extract",
        "include": "extract",
        "exclude": "exclude",
        "remove": "exclude",
        "drop": "exclude",
        "delete": "exclude",
    }
    if candidate in aliases:
        return aliases[candidate]
    raise ValueError(
        "Unsupported action. Use one of: extract, keep, retain, preserve, include, exclude, remove, drop, delete."
    )


def _default_prefix_for_action(action: str) -> str:
    return "baoliuweidian" if action == "extract" else "tichuweidian"


@dataclass
class PreparedLocusSubsetRun:
    """Prepared PLINK locus keep/remove execution plan."""

    launcher: str
    action: str
    prefix: str
    command: list[str]
    bfile_prefix_path: Path
    loci_input_label: str
    normalized_loci_list_path: Path
    output_dir: Path
    subset_prefix_path: Path
    bed_prefix_path: Path
    vcf_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "action": self.action,
            "prefix": self.prefix,
            "bfile_prefix_path": str(self.bfile_prefix_path),
            "loci_input_label": self.loci_input_label,
            "normalized_loci_list_path": str(self.normalized_loci_list_path),
            "output_dir": str(self.output_dir),
            "subset_prefix_path": str(self.subset_prefix_path),
            "bed_prefix_path": str(self.bed_prefix_path),
            "vcf_path": str(self.vcf_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunLocusSubsetTool(PlinkToolBase, Tool):
    """Keep or remove specified loci from a PLINK BFILE dataset."""

    loci_list_format_hint = (
        "Provide one locus ID per line. Example:\n"
        "chr1.s_667117\n"
        "chr1.s_915373\n"
        "chr1.s_1022873\n"
        "chr1.s_1065915\n"
        "chr1.s_1069916\n"
        "chr1.s_1102676\n"
        "chr1.s_1154593\n"
        "chr1.s_1172097\n"
        "chr1.s_1173275\n"
        "chr1.s_1240840"
    )

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="locus_subset_analysis",
            default_output_subdir="locus_subset",
        )
        self.script_path = self.skill_dir / "locus_subset.sh"
        self.summary_script_path = self.skill_dir / "summarize_locus_subset.py"

    @property
    def name(self) -> str:
        return "run_locus_subset"

    @property
    def description(self) -> str:
        return (
            "Keep or remove specified loci from a PLINK BFILE dataset, export PED/MAP, rebuild "
            "BED/BIM/FAM, and export a subset VCF using the EasyGS_2 environment."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        example = (
            "Example locus IDs:\n"
            "chr1.s_667117\n"
            "chr1.s_915373\n"
            "chr1.s_1022873\n"
            "chr1.s_1065915\n"
            "chr1.s_1069916\n"
            "chr1.s_1102676\n"
            "chr1.s_1154593\n"
            "chr1.s_1172097\n"
            "chr1.s_1173275\n"
            "chr1.s_1240840"
        )
        return {
            "type": "object",
            "properties": {
                "bfile_prefix": {
                    "type": "string",
                    "description": "PLINK binary prefix for input BED/BIM/FAM files. Defaults to 'filter'.",
                },
                "action": {
                    "type": "string",
                    "description": "Subset action: extract/keep or exclude/remove. Defaults to extract.",
                },
                "extract": {
                    "type": "string",
                    "description": (
                        "Required for extract mode. Provide a loci list file path or inline locus IDs for "
                        "PLINK --extract.\n"
                        f"{example}"
                    ),
                },
                "exclude": {
                    "type": "string",
                    "description": (
                        "Required for exclude mode. Provide a loci list file path or inline locus IDs for "
                        "PLINK --exclude.\n"
                        f"{example}"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/locus_subset/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for subset outputs. Defaults to 'baoliuweidian' for extract "
                        "and 'tichuweidian' for exclude."
                    ),
                },
            },
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        extract_value = str(params.get("extract", "") or "").strip()
        exclude_value = str(params.get("exclude", "") or "").strip()
        if extract_value and exclude_value:
            errors.append("provide only one of extract or exclude")
        if not extract_value and not exclude_value:
            errors.append("one of extract or exclude is required")
        return errors

    async def execute(
        self,
        bfile_prefix: str = "filter",
        action: str = "extract",
        extract: str | None = None,
        exclude: str | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                action=action,
                extract=extract,
                exclude=exclude,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Locus subset analysis failed.\n"
                f"- Action: {prepared.action}\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- Loci input: {prepared.loci_input_label}\n"
                f"- Output prefix: {prepared.subset_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Locus subset analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Action: {prepared.action}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- Loci input: {prepared.loci_input_label}",
            f"- Normalized loci list: {prepared.normalized_loci_list_path}",
            f"- Output dir: {prepared.output_dir}",
            f"- Subset PED prefix: {prepared.subset_prefix_path}",
            f"- Intermediate BED prefix: {prepared.bed_prefix_path}",
            f"- Exported VCF: {prepared.vcf_path}",
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
        bfile_prefix: str = "filter",
        action: str = "extract",
        extract: str | None = None,
        exclude: str | None = None,
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedLocusSubsetRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        resolved_action, loci_value = self._resolve_loci_argument(
            action=action,
            extract=extract,
            exclude=exclude,
        )

        output_root = self._resolve_output_dir(output_dir)
        prefix_name = self._normalize_prefix_name(prefix, _default_prefix_for_action(resolved_action))
        subset_prefix_path = output_root / prefix_name
        bed_prefix_path = output_root / f"{prefix_name}_turn"
        vcf_path = subset_prefix_path.with_suffix(".vcf")
        summary_path = output_root / f"{prefix_name}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        normalized_loci_list_path, loci_input_label, normalize_note = self._normalize_loci_list(
            loci_value,
            output_root,
            resolved_action,
            prefix_name,
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
            "--bfile",
            str(bfile_prefix_path),
            "--action",
            resolved_action,
            "--loci-list",
            str(normalized_loci_list_path),
            "--loci-input-label",
            loci_input_label,
            "--subset-prefix",
            str(subset_prefix_path),
            "--bed-prefix",
            str(bed_prefix_path),
            "--summary-output",
            str(summary_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        notes = [normalize_note] if normalize_note else []
        return PreparedLocusSubsetRun(
            launcher=env_status["launcher"],
            action=resolved_action,
            prefix=prefix_name,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            loci_input_label=loci_input_label,
            normalized_loci_list_path=normalized_loci_list_path,
            output_dir=output_root,
            subset_prefix_path=subset_prefix_path,
            bed_prefix_path=bed_prefix_path,
            vcf_path=vcf_path,
            summary_path=summary_path,
            notes=notes,
        )

    def _resolve_loci_argument(
        self,
        *,
        action: str,
        extract: str | None,
        exclude: str | None,
    ) -> tuple[str, str]:
        extract_value = (extract or "").strip()
        exclude_value = (exclude or "").strip()
        if extract_value and exclude_value:
            raise ValueError("Provide only one of extract or exclude.")
        if extract_value:
            return "extract", extract_value
        if exclude_value:
            return "exclude", exclude_value
        resolved_action = _normalize_action(action)
        expected_param = "extract" if resolved_action == "extract" else "exclude"
        raise ValueError(
            f"Loci list is required. Please provide `{expected_param}` as a file path or inline locus IDs.\n"
            f"{self.loci_list_format_hint}"
        )

    def _normalize_loci_list(
        self,
        loci_value: str,
        output_root: Path,
        action: str,
        prefix_name: str,
    ) -> tuple[Path, str, str]:
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = output_root / f"{prefix_name}_{action}_loci.txt"
        raw_value = loci_value.strip()
        if not raw_value:
            raise ValueError(f"Loci list is empty.\n{self.loci_list_format_hint}")

        if "\n" in raw_value or "\r" in raw_value:
            entries = self._parse_loci_text(raw_value)
            source_label = f"inline {action} parameter"
        else:
            candidate_path = _resolve_path(raw_value, self.allowed_dir)
            if candidate_path.exists():
                if not candidate_path.is_file():
                    raise ValueError(f"Loci list must be a file: {candidate_path}")
                entries = self._read_loci_file(candidate_path)
                source_label = str(candidate_path)
            elif self._looks_like_path(raw_value):
                raise ValueError(f"Loci list not found: {candidate_path}\n{self.loci_list_format_hint}")
            else:
                entries = self._parse_loci_text(raw_value)
                source_label = f"inline {action} parameter"

        if entries and self._looks_like_locus_header(entries[0]):
            entries = entries[1:]
        normalized_entries = [entry for entry in entries if entry]
        if not normalized_entries:
            raise ValueError(f"Loci list must contain at least one locus ID.\n{self.loci_list_format_hint}")

        output_path.write_text("\n".join(normalized_entries) + "\n", encoding="utf-8")
        return output_path, source_label, f"Normalized loci list to one-ID-per-line format: {output_path}"

    def _read_loci_file(self, path: Path) -> list[str]:
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
        return self._parse_loci_text(path.read_text(encoding="utf-8", errors="replace"))

    def _parse_loci_text(self, text: str) -> list[str]:
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

    def _looks_like_locus_header(self, value: str) -> bool:
        candidate = value.strip().lower().replace("-", "_").replace(" ", "_")
        return candidate in {"id", "ids", "marker", "marker_id", "markers", "locus", "locus_id", "variant", "variant_id", "snp", "snp_id"}
