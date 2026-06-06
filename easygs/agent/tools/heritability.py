"""Heritability analysis tool backed by the bundled GCTA pipeline."""

import asyncio
import csv
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path

@dataclass
class PreparedHeritabilityRun:  # 遗传力专用准备结果
    """Prepared heritability execution plan."""

    launcher: str
    prefix: str
    command: list[str]
    vcf_path: Path
    pheno_path: Path
    keep_path: Path | None
    bed_path: Path
    grm_path: Path
    result_path: Path
    notes: list[str] = field(default_factory=list)

    @property
    def result_prefix(self) -> Path:
        return self.result_path / self.prefix

    def to_metadata(self) -> dict[str, Any]:
        """Convert the prepared run into JSON-safe metadata."""
        return {
            "launcher": self.launcher,
            "prefix": self.prefix,
            "vcf_path": str(self.vcf_path),
            "pheno_path": str(self.pheno_path),
            "keep_path": str(self.keep_path) if self.keep_path else "",
            "bed_dir": str(self.bed_path),
            "grm_dir": str(self.grm_path),
            "result_dir": str(self.result_path),
            "result_prefix": str(self.result_prefix),
            "notes": list(self.notes),
        }



class RunHeritabilityTool(Tool):
    """Tool to run the bundled heritability analysis pipeline."""

    def __init__(
        self,
        workspace: Path,
        restrict_to_workspace: bool = False,
        timeout: int = 3600,
    ):
        self.workspace = workspace
        self.timeout = timeout
        self.allowed_dir = workspace if restrict_to_workspace else None
        self.script_path = (
            Path(__file__).resolve().parents[2]
            / "skills"
            / "heritability"
            / "scripts"
            / "heritability.sh"
        )
        self.env_name = "EasyGS_2"

    @property
    def name(self) -> str:
        return "run_heritability"

    @property
    def description(self) -> str:
        return (
            "Run the bundled single-trait GCTA heritability pipeline from VCF genotype data. "
            f"The tool always checks the {self.env_name} environment before execution."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "vcf": {
                    "type": "string",
                    "description": "Path to the input VCF or VCF.GZ file.",
                },
                "pheno": {
                    "type": "string",
                    "description": (
                        "Path to the tab-delimited phenotype table in three-column format: "
                        "FID, IID, and one trait column for a single heritability run."
                    ),
                },
                "keep": {
                    "type": "string",
                    "description": "Path to the sample list file.",
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Optional basename for BED/GRM/REML outputs. "
                        "If omitted, use the sample-list stem when keep is provided, "
                        "otherwise use the VCF stem."
                    ),
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional root output directory. When provided, the tool derives "
                        "bed/, grm/, and result/ subdirectories. If omitted in foreground "
                        "mode, the tool uses workspace/default_results/heritability/."
                    ),
                },
                "bed_dir": {
                    "type": "string",
                    "description": "Optional explicit output directory for PLINK BED files.",
                },
                "grm_dir": {
                    "type": "string",
                    "description": "Optional explicit output directory for GRM files.",
                },
                "result_dir": {
                    "type": "string",
                    "description": "Optional explicit output directory for GCTA result files.",
                },
            },
            "required": ["vcf", "pheno"],
        }

    async def execute(
        self,
        vcf: str,
        pheno: str,
        keep: str | None = None,
        prefix: str | None = None,
        output_dir: str | None = None,
        bed_dir: str | None = None,
        grm_dir: str | None = None,
        result_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        with tempfile.TemporaryDirectory(prefix="easygs-heritability-") as tmp_root:
            try:
                prepared = await self.prepare_run(
                    vcf=vcf,
                    pheno=pheno,
                    keep=keep,
                    prefix=prefix,
                    output_dir=output_dir,
                    bed_dir=bed_dir,
                    grm_dir=grm_dir,
                    result_dir=result_dir,
                    work_root=Path(tmp_root),
                )
            except (PermissionError, ValueError) as e:
                return f"Error: {e}"

            run_result = await self._run_command(prepared.command, timeout=self.timeout)
            if run_result["returncode"] != 0:
                return self._format_run_failure(
                    run_result=run_result,
                    prepared=prepared,
                )

            return self._format_run_success(
                prepared=prepared,
                stdout=run_result["stdout"],
                stderr=run_result["stderr"],
            )

    async def prepare_run(  # 准备好各种参数
        self,
        *,
        vcf: str,
        pheno: str,
        keep: str | None = None,
        prefix: str | None = None,
        output_dir: str | None = None,
        bed_dir: str | None = None,
        grm_dir: str | None = None,
        result_dir: str | None = None,
        work_root: Path,
    ) -> PreparedHeritabilityRun:
        """Resolve inputs and build the command for a heritability run."""
        vcf_path = _resolve_path(vcf, self.allowed_dir)
        pheno_path = _resolve_path(pheno, self.allowed_dir)
        keep_path = _resolve_path(keep, self.allowed_dir) if keep else None
        bed_path, grm_path, result_path = self._resolve_output_dirs(
            output_dir=output_dir,
            bed_dir=bed_dir,
            grm_dir=grm_dir,
            result_dir=result_dir,
        )

        for label, path in {
            "VCF": vcf_path,
            "phenotype": pheno_path,
            "pipeline script": self.script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")
        if keep_path is not None and not keep_path.exists():
            raise ValueError(f"sample list not found: {keep_path}")

        if not vcf_path.is_file() or not pheno_path.is_file() or (keep_path is not None and not keep_path.is_file()):
            raise ValueError("VCF and phenotype inputs must be files, and keep must be a file when provided")

        env_status = await self._get_environment_status()
        if env_status["error"]:
            raise ValueError(env_status["error"][7:] if env_status["error"].startswith("Error: ") else env_status["error"])

        work_root.mkdir(parents=True, exist_ok=True)
        normalized_pheno, pheno_note = self._normalize_phenotype_input(pheno_path, work_root)
        normalized_keep, keep_note = self._normalize_keep_input(keep_path, work_root) if keep_path else (None, "")
        self._validate_phenotype_file(normalized_pheno)

        prefix_name = self._resolve_prefix(prefix, keep_path, vcf_path)
        command = [
            env_status["launcher"],
            "run",
            "-n",
            self.env_name,
            "bash",
            str(self.script_path),
            "--vcf",
            str(vcf_path),
            "--pheno",
            str(normalized_pheno),
            "--prefix",
            prefix_name,
            "--bed-dir",
            str(bed_path),
            "--grm-dir",
            str(grm_path),
            "--result-dir",
            str(result_path),
        ]
        if normalized_keep is not None:
            command.extend(["--keep", str(normalized_keep)])
        notes = [note for note in (pheno_note, keep_note) if note]
        return PreparedHeritabilityRun(
            launcher=env_status["launcher"],
            prefix=prefix_name,
            command=command,
            vcf_path=vcf_path,
            pheno_path=pheno_path,
            keep_path=keep_path,
            bed_path=bed_path,
            grm_path=grm_path,
            result_path=result_path,
            notes=notes,
        )

    def _resolve_output_dirs(
        self,
        output_dir: str | None,
        bed_dir: str | None,
        grm_dir: str | None,
        result_dir: str | None,
    ) -> tuple[Path, Path, Path]:
        if output_dir:
            root = _resolve_path(output_dir, self.allowed_dir)
            bed_path = _resolve_path(bed_dir, self.allowed_dir) if bed_dir else root / "bed"
            grm_path = _resolve_path(grm_dir, self.allowed_dir) if grm_dir else root / "grm"
            result_path = _resolve_path(result_dir, self.allowed_dir) if result_dir else root / "result"
            return bed_path, grm_path, result_path

        if bed_dir and grm_dir and result_dir:
            return (
                _resolve_path(bed_dir, self.allowed_dir),
                _resolve_path(grm_dir, self.allowed_dir),
                _resolve_path(result_dir, self.allowed_dir),
            )

        default_root = self.workspace / "default_results" / "heritability"
        return default_root / "bed", default_root / "grm", default_root / "result"

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
                    "Create or activate it before running heritability analysis."
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
                    "command -v vcftools >/dev/null && command -v plink >/dev/null && command -v gcta64 >/dev/null",
                ],
                timeout=60,
            )
            if tool_check["returncode"] == 0:
                return {"launcher": launcher, "error": ""}

            details = self._join_output(tool_check["stdout"], tool_check["stderr"])
            launcher_errors.append(f"{launcher}: {details or 'missing required executables'}")

        if env_missing_error and not launcher_errors:
            return {"launcher": "", "error": env_missing_error}

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

    def _normalize_phenotype_input(self, pheno_path: Path, tmp_root: Path) -> tuple[Path, str]:
        if pheno_path.suffix.lower() != ".csv":
            return pheno_path, ""

        output_path = tmp_root / f"{pheno_path.stem}.tsv"
        with pheno_path.open("r", encoding="utf-8", newline="") as src, output_path.open(
            "w", encoding="utf-8", newline=""
        ) as dst:
            reader = csv.reader(src)
            writer = csv.writer(dst, delimiter="\t")
            rows_written = 0
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue
                writer.writerow(row)
                rows_written += 1
        if rows_written < 2:
            raise ValueError(f"Phenotype CSV must contain a header and at least one sample row: {pheno_path}")
        return output_path, f"Normalized phenotype CSV to TSV: {output_path}"

    def _validate_phenotype_file(self, pheno_path: Path) -> None:
        """Validate the required FID/IID/trait tab-delimited phenotype format."""
        lines = pheno_path.read_text(encoding="utf-8").splitlines()
        non_empty = [line for line in lines if line.strip()]
        if len(non_empty) < 2:
            raise ValueError(f"Phenotype file must contain a header and at least one sample row: {pheno_path}")

        header = non_empty[0].split("\t")
        if len(header) != 3 or header[0] != "FID" or header[1] != "IID" or not header[2].strip():
            raise ValueError(
                "Phenotype file must be tab-delimited with exactly three columns: FID, IID, and one trait column"
            )

        first_row = non_empty[1].split("\t")
        if len(first_row) != 3:
            raise ValueError(
                "Phenotype file must be tab-delimited with exactly three columns in each row"
            )

    def _normalize_keep_input(self, keep_path: Path, tmp_root: Path) -> tuple[Path, str]:
        if keep_path.suffix.lower() not in {".csv", ".tsv"}:
            return keep_path, ""

        delimiter = "," if keep_path.suffix.lower() == ".csv" else "\t"
        output_path = tmp_root / f"{keep_path.stem}.txt"
        sample_ids: list[str] = []
        with keep_path.open("r", encoding="utf-8", newline="") as src:
            reader = csv.reader(src, delimiter=delimiter)
            for row in reader:
                if not row or not row[0].strip():
                    continue
                sample_ids.append(row[0].strip())

        if sample_ids and self._looks_like_header(sample_ids[0]):
            sample_ids = sample_ids[1:]
        if not sample_ids:
            raise ValueError(f"Sample list must contain at least one sample ID: {keep_path}")

        output_path.write_text("\n".join(sample_ids) + "\n", encoding="utf-8")
        return output_path, f"Normalized sample list to plain text: {output_path}"

    def _resolve_prefix(self, prefix: str | None, keep_path: Path | None, vcf_path: Path) -> str:
        candidate = (prefix or "").strip()
        if candidate:
            return candidate
        if keep_path is not None:
            return keep_path.stem
        name = vcf_path.name
        if name.endswith(".vcf.gz"):
            return name[: -len(".vcf.gz")]
        if name.endswith(".vcf"):
            return name[: -len(".vcf")]
        return vcf_path.stem

    def _looks_like_header(self, value: str) -> bool:
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        return normalized in {"sample", "sample_id", "sampleid", "id", "taxa", "line"}

    def _format_run_failure(self, run_result: dict[str, str | int], prepared: PreparedHeritabilityRun) -> str:
        details = self._join_output(run_result["stdout"], run_result["stderr"])
        return (
            "Error: Heritability analysis failed.\n"
            "Resolved inputs:\n"
            f"- VCF: {prepared.vcf_path}\n"
            f"- Phenotype: {prepared.pheno_path}\n"
            f"- Sample list: {prepared.keep_path or 'not provided (full VCF mode)'}\n"
            "Resolved outputs:\n"
            f"- BED dir: {prepared.bed_path}\n"
            f"- GRM dir: {prepared.grm_path}\n"
            f"- Result dir: {prepared.result_path}\n"
            f"Exit code: {run_result['returncode']}\n"
            f"{details}"
        ).strip()

    def _format_run_success(
        self,
        prepared: PreparedHeritabilityRun,
        stdout: str,
        stderr: str,
    ) -> str:
        result_prefix = prepared.result_prefix
        summary = self._summarize_hsq(result_prefix.with_suffix(".hsq"))
        lines = [
            "Heritability analysis completed.",
            f"- Launcher: {prepared.launcher}",
            f"- VCF: {prepared.vcf_path}",
            f"- Phenotype: {prepared.pheno_path}",
            f"- Sample list: {prepared.keep_path or 'not provided (full VCF mode)'}",
            f"- BED dir: {prepared.bed_path}",
            f"- GRM dir: {prepared.grm_path}",
            f"- Result dir: {prepared.result_path}",
            f"- Result prefix: {result_prefix}",
        ]
        if prepared.notes:
            lines.extend(f"- Note: {note}" for note in prepared.notes)
        if summary:
            lines.append(f"- Estimated h2 (V(G)/Vp): {summary}")
        details = self._join_output(stdout, stderr)
        if details:
            lines.append("")
            lines.append(details)
        return "\n".join(lines)

    def _summarize_hsq(self, hsq_path: Path) -> str:
        if not hsq_path.exists():
            return ""
        try:
            for line in hsq_path.read_text(encoding="utf-8").splitlines():
                parts = re.split(r"\s+", line.strip())
                if len(parts) >= 3 and parts[0] == "V(G)/Vp":
                    return f"{parts[1]} (SE {parts[2]})"
        except Exception:
            return ""
        return ""

    def _join_output(self, stdout: Any, stderr: Any) -> str:
        parts: list[str] = []
        if isinstance(stdout, str) and stdout.strip():
            parts.append(stdout.strip())
        if isinstance(stderr, str) and stderr.strip():
            parts.append(f"STDERR:\n{stderr.strip()}")
        return "\n".join(parts).strip()
