"""Peak/locus structural annotation tool backed by ChIPseeker."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
_BUILTIN_MAIZE_GFF3 = Path("/home/wlg/easyGP/pubdata/Zea_mays.B73_RefGen_v4.43_modify.gff3").resolve()


@dataclass
class PreparedPeakAnnotationRun:
    """Prepared execution plan for peak annotation."""

    launcher: str
    tss_upstream: int
    tss_downstream: int
    command: list[str]
    gff3_path: Path
    bed_path: Path
    output_dir: Path
    output_prefix_path: Path
    result_tsv_path: Path
    plot_png_path: Path
    summary_path: Path
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        return {
            "launcher": self.launcher,
            "tss_upstream": self.tss_upstream,
            "tss_downstream": self.tss_downstream,
            "gff3_path": str(self.gff3_path),
            "bed_path": str(self.bed_path),
            "output_dir": str(self.output_dir),
            "output_prefix_path": str(self.output_prefix_path),
            "result_tsv_path": str(self.result_tsv_path),
            "plot_png_path": str(self.plot_png_path),
            "summary_path": str(self.summary_path),
            "notes": list(self.notes),
        }



class RunPeakAnnotationTool(PlinkToolBase, Tool):
    """Run maize-only ChIPseeker locus/peak structural annotation from BED input."""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 3600):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="peak_annotation_analysis",
            default_output_subdir="peak_annotation",
            env_name="EasyGS_1",
        )
        self.script_path = self.skill_dir / "peak_annotation.sh"
        self.r_script_path = self.skill_dir / "run_peak_annotation.R"
        self.summary_script_path = self.skill_dir / "summarize_peak_annotation.py"

    @property
    def name(self) -> str:
        return "run_peak_annotation"

    @property
    def description(self) -> str:
        return (
            "Run maize-only ChIPseeker-based locus structural annotation in EasyGS_1 using the "
            "built-in Zea mays B73 RefGen v4.43 annotation and a BED file, then export annotation "
            "TSV and annotation pie-chart PNG outputs."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gff3": {
                    "type": "string",
                    "description": (
                        "Optional maize gene annotation path. Defaults to the built-in maize "
                        f"annotation: {_BUILTIN_MAIZE_GFF3}. "
                        "This tool is maize-only and does not accept non-maize annotations."
                    ),
                },
                "bed": {
                    "type": "string",
                    "description": (
                        "BED file containing loci/peaks to annotate. Example:\n"
                        "1\t207606062\t207606063\n"
                        "2\t180017154\t180017155\n"
                        "2\t191156851\t191156852\n"
                        "2\t195873477\t195873478"
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. Defaults to "
                        "workspace/default_results/peak_annotation/. If you want to override it, "
                        "please provide it explicitly."
                    ),
                },
                "output_prefix": {
                    "type": "string",
                    "description": (
                        "Optional basename or path prefix for outputs. Defaults to the BED stem, "
                        "for example locilist -> locilist.peakanno.tsv / locilist.peakanno.png. "
                        "If you want to override it, please provide it explicitly."
                    ),
                },
                "tss_upstream": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Upstream TSS annotation window in bp. Default: 2000. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
                "tss_downstream": {
                    "type": "integer",
                    "minimum": 0,
                    "description": (
                        "Downstream TSS annotation window in bp. Default: 500. If you want to "
                        "override it, please provide it explicitly."
                    ),
                },
            },
            "required": ["bed"],
        }

    async def execute(
        self,
        bed: str,
        gff3: str | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        tss_upstream: int | None = None,
        tss_downstream: int | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                bed=bed,
                gff3=gff3,
                output_dir=output_dir,
                output_prefix=output_prefix,
                tss_upstream=tss_upstream,
                tss_downstream=tss_downstream,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: Peak annotation analysis failed.\n"
                f"- GFF3: {prepared.gff3_path}\n"
                f"- BED: {prepared.bed_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "Peak annotation analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- GFF3: {prepared.gff3_path}",
            f"- BED: {prepared.bed_path}",
            f"- TSS window: -{prepared.tss_upstream}bp to +{prepared.tss_downstream}bp",
            f"- Output dir: {prepared.output_dir}",
            f"- Annotation TSV: {prepared.result_tsv_path}",
            f"- Annotation PNG: {prepared.plot_png_path}",
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
        bed: str,
        gff3: str | None = None,
        output_dir: str | None = None,
        output_prefix: str | None = None,
        tss_upstream: int | None = None,
        tss_downstream: int | None = None,
    ) -> PreparedPeakAnnotationRun:
        gff3_path = self._resolve_gff_file(gff3)
        bed_path = self._resolve_bed_file(bed)
        self._validate_bed_preview(bed_path)
        output_root = self._resolve_output_dir(output_dir)
        output_prefix_path = self._resolve_output_prefix(output_prefix, output_root, bed_path)

        tss_upstream_value = int(tss_upstream if tss_upstream is not None else 2000)
        tss_downstream_value = int(tss_downstream if tss_downstream is not None else 500)
        if tss_upstream_value < 0:
            raise ValueError("tss_upstream must be >= 0")
        if tss_downstream_value < 0:
            raise ValueError("tss_downstream must be >= 0")

        result_tsv_path = output_prefix_path.parent / f"{output_prefix_path.name}.peakanno.tsv"
        plot_png_path = output_prefix_path.parent / f"{output_prefix_path.name}.peakanno.png"
        summary_path = output_prefix_path.parent / f"{output_prefix_path.name}.peakanno_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "R script": self.r_script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["Rscript", "python3"])
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
            "--gff3",
            str(gff3_path),
            "--bed",
            str(bed_path),
            "--output-tsv",
            str(result_tsv_path),
            "--output-png",
            str(plot_png_path),
            "--summary-output",
            str(summary_path),
            "--tss-upstream",
            str(tss_upstream_value),
            "--tss-downstream",
            str(tss_downstream_value),
            "--r-script",
            str(self.r_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedPeakAnnotationRun(
            launcher=env_status["launcher"],
            tss_upstream=tss_upstream_value,
            tss_downstream=tss_downstream_value,
            command=command,
            gff3_path=gff3_path,
            bed_path=bed_path,
            output_dir=output_prefix_path.parent,
            output_prefix_path=output_prefix_path,
            result_tsv_path=result_tsv_path,
            plot_png_path=plot_png_path,
            summary_path=summary_path,
        )

    def _resolve_gff_file(self, value: str | None) -> Path:
        if value and str(value).strip():
            path = Path(value).expanduser().resolve()
        else:
            path = _BUILTIN_MAIZE_GFF3

        if not path.exists():
            raise ValueError(f"GFF annotation file not found: {path}")
        if not path.is_file():
            raise ValueError(f"GFF annotation input must be a file: {path}")
        if path.suffix.lower() not in {".gff3", ".gff", ".gtf"}:
            raise ValueError(f"GFF annotation input must end with .gff3, .gff, or .gtf: {path}")
        if path != _BUILTIN_MAIZE_GFF3:
            raise ValueError(
                "Peak annotation is maize-only and only supports the built-in annotation: "
                f"{_BUILTIN_MAIZE_GFF3}"
            )
        return path

    def _resolve_bed_file(self, value: str) -> Path:
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"BED file not found: {path}")
        if not path.is_file():
            raise ValueError(f"BED input must be a file: {path}")
        if path.suffix.lower() != ".bed":
            raise ValueError(f"BED input must end with .bed: {path}")
        return path

    def _resolve_output_prefix(self, value: str | None, output_root: Path, bed_path: Path) -> Path:
        if value:
            raw = Path(value).expanduser()
            if raw.is_absolute():
                candidate = _resolve_path(str(raw), self.allowed_dir)
            else:
                candidate = _resolve_path(str(output_root / raw), self.allowed_dir)
        else:
            candidate = output_root / bed_path.stem
        name = candidate.name
        if name.endswith(".peakanno"):
            name = name[: -len(".peakanno")]
        if not name:
            name = bed_path.stem or "locilist"
        return candidate.parent / name

    def _validate_bed_preview(self, path: Path) -> None:
        valid_rows = 0
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    raise ValueError(f"BED file must have at least 3 tab-separated columns: {path}")
                try:
                    int(parts[1])
                    int(parts[2])
                except ValueError as exc:
                    raise ValueError(f"BED start/end columns must be integers: {path}") from exc
                valid_rows += 1
                if valid_rows >= 3:
                    break
        if valid_rows == 0:
            raise ValueError(f"BED file does not contain any valid data rows: {path}")
