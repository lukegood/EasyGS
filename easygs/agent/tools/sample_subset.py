"""Standalone PLINK sample keep/remove analysis tool."""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase

def _normalize_action(value: str | None) -> str:
    candidate = (value or "keep").strip().lower()
    aliases = {
        "keep": "keep",
        "retain": "keep",
        "preserve": "keep",
        "remove": "remove",
        "delete": "remove",
        "drop": "remove",
    }
    if candidate in aliases:
        return aliases[candidate]
    raise ValueError("Unsupported action. Use one of: keep, retain, preserve, remove, delete, drop.")


def _default_prefix_for_action(action: str) -> str:
    return "kept_samples" if action == "keep" else "remaining_samples"


@dataclass
class PreparedSampleSubsetRun:
    """Prepared PLINK sample keep/remove execution plan."""

    launcher: str
    action: str
    prefix: str
    command: list[str]
    bfile_prefix_path: Path
    sample_list_path: Path
    normalized_sample_list_path: Path
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
            "sample_list_path": str(self.sample_list_path),
            "normalized_sample_list_path": str(self.normalized_sample_list_path),
            "output_dir": str(self.output_dir),
            "subset_prefix_path": str(self.subset_prefix_path),
            "bed_prefix_path": str(self.bed_prefix_path),
            "vcf_path": str(self.vcf_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunSampleSubsetTool(PlinkToolBase, Tool):
    """Keep or remove a specified list of samples and export a subset VCF."""

    sample_list_format_hint = (
        "The sample list file must contain two whitespace- or tab-delimited columns: FID and IID. "
        "Example:\nMG_890 MG_890\nMG_1254 MG_1254\nMG_689 MG_689"
    )

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="sample_subset_analysis",
            default_output_subdir="sample_subset",
        )
        self.script_path = self.skill_dir / "sample_subset.sh"
        self.summary_script_path = self.skill_dir / "summarize_sample_subset.py"

    @property
    def name(self) -> str:
        return "run_sample_subset"

    @property
    def description(self) -> str:
        return (
            "Keep or remove a specified set of samples from a PLINK BFILE dataset, export PED/MAP, "
            "rebuild BED/BIM/FAM, and export a subset VCF using the EasyGS_2 environment."
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
                "sample_list": {
                    "type": "string",
                    "description": (
                        "Path to the two-column FID/IID sample list file. "
                        "Example rows: 'MG_890 MG_890', 'MG_1254 MG_1254'."
                    ),
                },
                "action": {
                    "type": "string",
                    "description": "Subset action: keep or remove. Defaults to keep.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. If omitted, foreground runs default to "
                        "workspace/default_results/sample_subset/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Basename for subset outputs. Defaults to 'kept_samples' for keep and "
                        "'remaining_samples' for remove."
                    ),
                },
            },
            "required": ["bfile_prefix", "sample_list"],
        }

    async def execute(
        self,
        bfile_prefix: str,
        sample_list: str,
        action: str = "keep",
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bfile_prefix=bfile_prefix,
                sample_list=sample_list,
                action=action,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Sample subset analysis failed.\n"
                f"- Action: {prepared.action}\n"
                f"- Input BFILE: {prepared.bfile_prefix_path}\n"
                f"- Sample list: {prepared.sample_list_path}\n"
                f"- Output prefix: {prepared.subset_prefix_path}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Sample subset analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Action: {prepared.action}",
            f"- Input BFILE: {prepared.bfile_prefix_path}",
            f"- Sample list: {prepared.sample_list_path}",
            f"- Normalized sample list: {prepared.normalized_sample_list_path}",
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
        bfile_prefix: str,
        sample_list: str,
        action: str = "keep",
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedSampleSubsetRun:
        bfile_prefix_path = self._resolve_bfile_prefix(bfile_prefix)
        sample_list_path = _resolve_path(sample_list, self.allowed_dir)
        if not sample_list_path.exists():
            raise ValueError(f"Sample list not found: {sample_list_path}")
        if not sample_list_path.is_file():
            raise ValueError(f"Sample list must be a file: {sample_list_path}")

        output_root = self._resolve_output_dir(output_dir)
        resolved_action = _normalize_action(action)
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

        normalized_sample_list_path, normalize_note = self._normalize_sample_list(
            sample_list_path,
            output_root,
            resolved_action,
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
            "--sample-list",
            str(normalized_sample_list_path),
            "--original-sample-list",
            str(sample_list_path),
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
        return PreparedSampleSubsetRun(
            launcher=env_status["launcher"],
            action=resolved_action,
            prefix=prefix_name,
            command=command,
            bfile_prefix_path=bfile_prefix_path,
            sample_list_path=sample_list_path,
            normalized_sample_list_path=normalized_sample_list_path,
            output_dir=output_root,
            subset_prefix_path=subset_prefix_path,
            bed_prefix_path=bed_prefix_path,
            vcf_path=vcf_path,
            summary_path=summary_path,
            notes=notes,
        )

    def _normalize_sample_list(
        self,
        sample_list_path: Path,
        output_root: Path,
        action: str,
    ) -> tuple[Path, str]:
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = output_root / f"{sample_list_path.stem}_{action}_fid_iid.txt"
        suffix = sample_list_path.suffix.lower()
        rows: list[list[str]] = []

        if suffix in {".csv", ".tsv"}:
            delimiter = "," if suffix == ".csv" else "\t"
            with sample_list_path.open("r", encoding="utf-8", newline="") as src:
                reader = csv.reader(src, delimiter=delimiter)
                for row in reader:
                    cleaned = [cell.strip() for cell in row if cell.strip()]
                    if cleaned:
                        rows.append(cleaned)
        else:
            for line in sample_list_path.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                rows.append([cell for cell in re.split(r"[\s,]+", stripped) if cell])

        if rows and self._looks_like_fid_iid_header(rows[0]):
            rows = rows[1:]
        if not rows:
            raise ValueError(
                "Sample list must contain at least one FID/IID row.\n"
                f"{self.sample_list_format_hint}"
            )

        normalized_rows: list[tuple[str, str]] = []
        for row in rows:
            if len(row) < 2 or not row[0].strip() or not row[1].strip():
                raise ValueError(
                    "Sample list must contain at least two columns: FID and IID.\n"
                    f"{self.sample_list_format_hint}"
                )
            normalized_rows.append((row[0].strip(), row[1].strip()))

        output_path.write_text(
            "\n".join(f"{fid}\t{iid}" for fid, iid in normalized_rows) + "\n",
            encoding="utf-8",
        )
        return output_path, f"Normalized sample list to tab-delimited FID/IID format: {output_path}"

    def _looks_like_fid_iid_header(self, row: list[str]) -> bool:
        if len(row) < 2:
            return False
        first = row[0].strip().lower().replace("-", "_").replace(" ", "_")
        second = row[1].strip().lower().replace("-", "_").replace(" ", "_")
        fid_aliases = {"fid", "family", "family_id"}
        iid_aliases = {"iid", "id", "sample", "sample_id", "line"}
        return first in fid_aliases and second in iid_aliases
