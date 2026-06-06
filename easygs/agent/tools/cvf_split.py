"""CVF 划分工具。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool
from easygs.agent.tools.filesystem import _resolve_path
from easygs.agent.tools.plink_common import PlinkToolBase
_ALLOWED_SAMPLE_HEADERS = (
    "id",
    "list_id",
    "sample_id",
    "line_id",
    "material_id",
    "sampleid",
    "lineid",
    "materialid",
    "listid",
)


@dataclass
class PreparedCvfSplitRun:
    """CVF 划分的预处理结果。"""

    launcher: str
    command: list[str]
    list_txt_path: Path
    output_dir: Path
    output_csv_path: Path
    summary_path: Path
    sample_column: str
    cv_column: str
    folds: int
    seed: int
    sample_count: int
    prefix: str
    notes: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict[str, Any]:
        """转成可序列化元数据。"""
        return {
            "launcher": self.launcher,
            "list_txt_path": str(self.list_txt_path),
            "output_dir": str(self.output_dir),
            "output_csv_path": str(self.output_csv_path),
            "summary_path": str(self.summary_path),
            "sample_column": self.sample_column,
            "cv_column": self.cv_column,
            "folds": self.folds,
            "seed": self.seed,
            "sample_count": self.sample_count,
            "prefix": self.prefix,
            "notes": list(self.notes),
        }



class RunCvfSplitTool(PlinkToolBase, Tool):
    """根据材料 LIST 生成 CVF CSV。"""

    def __init__(self, workspace: Path, restrict_to_workspace: bool = False, timeout: int = 1800):
        super().__init__(
            workspace,
            restrict_to_workspace,
            timeout,
            skill_name="cvf_split_analysis",
            default_output_subdir="cvf_split",
            env_name="EasyGS_3",
        )
        self.script_path = self.skill_dir / "cvf_split.sh"
        self.run_script_path = self.skill_dir / "run_cvf_split.py"
        self.summary_script_path = self.skill_dir / "summarize_cvf_split.py"

    @property
    def name(self) -> str:
        return "run_cvf_split"

    @property
    def description(self) -> str:
        return (
            "Generate a cross-validation fold CSV from a one-column material LIST TXT in EasyGS_3. "
            "The first line must be a supported sample column header such as ID or list_id, "
            "and the output CV column defaults to cv_1."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "list_txt": {
                    "type": "string",
                    "description": (
                        "Path to the one-column material LIST TXT. The first line must be a supported sample "
                        "column header such as ID, list_id, sample_id, line_id, or material_id. The remaining "
                        "lines must contain one material ID per line. Example:\n"
                        "ID\n"
                        "MG_001\n"
                        "MG_002\n"
                        "MG_003\n"
                        "MG_004"
                    ),
                },
                "k": {
                    "type": "integer",
                    "minimum": 2,
                    "description": "Fold count. Default: 10.",
                },
                "seed": {
                    "type": "integer",
                    "description": "Random seed used for reproducible shuffling. Default: 42.",
                },
                "cv_column": {
                    "type": "string",
                    "description": "Fold column name in the output CSV. Default: cv_1.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional output directory. In background workflows, omitting this value "
                        "writes to the current workflow action directory. Direct foreground runs "
                        "default to workspace/default_results/cvf_split/."
                    ),
                },
                "prefix": {
                    "type": "string",
                    "description": (
                        "Optional output basename. Default: <list_stem>_cvf_k<k>_seed<seed>."
                    ),
                },
            },
            "required": ["list_txt"],
        }

    async def execute(
        self,
        list_txt: str,
        k: int = 10,
        seed: int = 42,
        cv_column: str = "cv_1",
        output_dir: str | None = None,
        prefix: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            prepared = await self.prepare_run(
                list_txt=list_txt,
                k=k,
                seed=seed,
                cv_column=cv_column,
                output_dir=output_dir,
                prefix=prefix,
            )
        except (PermissionError, ValueError) as e:
            return f"Error: {e}"

        run_result = await self._run_command(prepared.command, timeout=self.timeout)
        if run_result["returncode"] != 0:
            details = self._join_output(run_result["stdout"], run_result["stderr"])
            return (
                "Error: CVF split failed.\n"
                f"- Input LIST: {prepared.list_txt_path}\n"
                f"- Output dir: {prepared.output_dir}\n"
                f"Exit code: {run_result['returncode']}\n"
                f"{details}"
            ).strip()

        lines = [
            "CVF split completed.",
            f"- Launcher: {prepared.launcher}",
            f"- Input LIST: {prepared.list_txt_path}",
            f"- Sample column: {prepared.sample_column}",
            f"- CV column: {prepared.cv_column}",
            f"- Fold count: {prepared.folds}",
            f"- Random seed: {prepared.seed}",
            f"- Sample count: {prepared.sample_count}",
            f"- Output dir: {prepared.output_dir}",
            f"- Output CSV: {prepared.output_csv_path}",
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
        list_txt: str,
        k: int = 10,
        seed: int = 42,
        cv_column: str = "cv_1",
        output_dir: str | None = None,
        prefix: str | None = None,
    ) -> PreparedCvfSplitRun:
        list_txt_path = self._resolve_list_txt(list_txt)
        sample_column, sample_ids = self._parse_list_txt(list_txt_path)

        folds = k or 10
        if folds < 2:
            raise ValueError("k must be at least 2.")
        if len(sample_ids) < folds:
            raise ValueError(
                f"Sample count must be greater than or equal to k. samples={len(sample_ids)}, k={folds}"
            )

        seed_value = seed if seed is not None else 42
        cv_column_value = (cv_column or "cv_1").strip() or "cv_1"
        output_root = self._resolve_output_dir(output_dir)
        prefix_value = self._normalize_prefix_name(
            prefix,
            f"{list_txt_path.stem}_cvf_k{folds}_seed{seed_value}",
        )
        output_csv_path = output_root / f"{prefix_value}.csv"
        summary_path = output_root / f"{prefix_value}_summary.txt"

        for label, path in {
            "pipeline script": self.script_path,
            "run script": self.run_script_path,
            "summary script": self.summary_script_path,
        }.items():
            if not path.exists():
                raise ValueError(f"{label} not found: {path}")

        env_status = await self._get_environment_status(["python3"])
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
            "--list-txt",
            str(list_txt_path),
            "--k",
            str(folds),
            "--seed",
            str(seed_value),
            "--sample-column",
            sample_column,
            "--cv-column",
            cv_column_value,
            "--output-csv",
            str(output_csv_path),
            "--summary-output",
            str(summary_path),
            "--run-script",
            str(self.run_script_path),
            "--summary-script",
            str(self.summary_script_path),
        ]

        return PreparedCvfSplitRun(
            launcher=env_status["launcher"],
            command=command,
            list_txt_path=list_txt_path,
            output_dir=output_root,
            output_csv_path=output_csv_path,
            summary_path=summary_path,
            sample_column=sample_column,
            cv_column=cv_column_value,
            folds=folds,
            seed=seed_value,
            sample_count=len(sample_ids),
            prefix=prefix_value,
        )

    def _resolve_list_txt(self, value: str) -> Path:
        """解析 LIST TXT 路径。"""
        path = _resolve_path(value, self.allowed_dir)
        if not path.exists():
            raise ValueError(f"Input LIST TXT not found: {path}")
        if not path.is_file():
            raise ValueError(f"Input LIST TXT must be a file: {path}")
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Input LIST TXT must end with .txt: {path}")
        return path

    def _parse_list_txt(self, path: Path) -> tuple[str, list[str]]:
        """读取并校验 LIST TXT 内容。"""
        lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        rows = [line for line in lines if line]
        if not rows:
            raise ValueError(f"LIST TXT is empty: {path}")

        sample_column = rows[0]
        sample_ids = rows[1:]
        if not sample_column:
            raise ValueError(f"LIST TXT header is empty: {path}")
        if sample_column.lower() not in _ALLOWED_SAMPLE_HEADERS:
            allowed_headers = ", ".join(_ALLOWED_SAMPLE_HEADERS)
            raise ValueError(
                "LIST TXT header must be one of the supported sample column names. "
                f"header={sample_column}, allowed={allowed_headers}"
            )
        if not sample_ids:
            raise ValueError(f"LIST TXT must contain a header and at least one material ID: {path}")

        duplicates: list[str] = []
        seen: set[str] = set()
        for sample_id in sample_ids:
            if not sample_id:
                raise ValueError(f"LIST TXT contains an empty material ID: {path}")
            if sample_id in seen and sample_id not in duplicates:
                duplicates.append(sample_id)
            seen.add(sample_id)

        if duplicates:
            duplicate_text = ", ".join(duplicates[:10])
            raise ValueError(f"LIST TXT contains duplicate material IDs: {duplicate_text}")
        return sample_column, sample_ids
