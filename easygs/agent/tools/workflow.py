"""Workflow-internal analysis action tools."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from easygs.agent.tools.base import Tool


BackgroundPrepareFn = Callable[[dict[str, Any], Path, Path], dict[str, Any]]
WorkflowCommandRunner = Callable[[list[str], Path, Path, Path], Awaitable[int]]


@dataclass(frozen=True)
class WorkflowDefinition:
    """Declarative definition for an analysis capability."""

    kind: str
    tool_name: str
    description: str
    run_tool: Tool
    prepare_background_kwargs: BackgroundPrepareFn

    def build_parameters(self) -> dict[str, Any]:
        """Expose the run-tool schema through the workflow action view."""
        schema = copy.deepcopy(self.run_tool.parameters)
        properties = schema.get("properties")
        if isinstance(properties, dict):
            output_dir = properties.get("output_dir")
            if isinstance(output_dir, dict):
                output_dir["description"] = (
                    "Optional directory for this workflow action's output files. "
                    "If omitted, the current workflow action output directory is used."
                )
        return schema


@dataclass
class WorkflowActionResult:
    """Result packet returned by workflow-internal tools."""

    content: str
    command: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    discovery_roots: list[Path] = field(default_factory=list)
    initial_files_by_root: dict[Path, set[str]] = field(default_factory=dict)
    exit_code: int | None = None
    error: str | None = None


class AnalysisActionTool(Tool):
    """Execute one registered analysis capability inside a workflow action directory."""

    def __init__(self, definition: WorkflowDefinition):
        self._definition = definition

    @property
    def name(self) -> str:
        return self._definition.tool_name

    @property
    def description(self) -> str:
        return (
            self._definition.description
            + " Runs as an action inside the current background workflow and returns produced files."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return self._definition.build_parameters()

    async def execute(self, **kwargs: Any) -> str:
        return (
            "Error: analysis action tools can only run inside a background workflow action. "
            "Submit a workflow request instead."
        )

    async def execute_workflow_action(
        self,
        *,
        args: dict[str, Any],
        action_dir: Path,
        stdout_path: Path,
        stderr_path: Path,
        default_output_dir: Path | None = None,
        command_runner: WorkflowCommandRunner | None = None,
    ) -> WorkflowActionResult:
        prepare_run = getattr(self._definition.run_tool, "prepare_run", None)
        if not callable(prepare_run):
            return WorkflowActionResult(
                content=f"Error: tool '{self.name}' does not support prepared workflow execution.",
                error=f"Tool '{self.name}' does not support prepared workflow execution.",
            )

        action_dir.mkdir(parents=True, exist_ok=True)
        prepared_kwargs = self._definition.prepare_background_kwargs(
            dict(args),
            action_dir,
            default_output_dir or action_dir,
        )
        try:
            prepared = await prepare_run(**prepared_kwargs)
        except Exception as exc:
            stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
            return WorkflowActionResult(
                content=f"Error preparing {self.name}: {exc}",
                error=str(exc),
            )

        to_metadata = getattr(prepared, "to_metadata", None)
        outputs = to_metadata() if callable(to_metadata) else {}
        outputs = outputs if isinstance(outputs, dict) else {}
        discovery_roots = _discovery_roots_from_outputs(
            outputs,
            fallback=default_output_dir or action_dir,
        )
        initial_files_by_root = {
            root: _snapshot_files(root)
            for root in discovery_roots
        }

        command = list(prepared.command)
        if command_runner is not None:
            exit_code = await command_runner(command, stdout_path, stderr_path, action_dir)
        else:
            exit_code = await self._run_command(
                command=command,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                cwd=action_dir,
            )

        if exit_code != 0:
            error = _read_tail(stderr_path) or f"Process exited with code {exit_code}"
            return WorkflowActionResult(
                content=(
                    f"Error: {self.name} failed with exit code {exit_code}.\n"
                    f"STDERR tail:\n{error}"
                ).strip(),
                command=command,
                outputs=outputs,
                discovery_roots=discovery_roots,
                initial_files_by_root=initial_files_by_root,
                exit_code=exit_code,
                error=error,
            )

        return WorkflowActionResult(
            content=self._format_success(outputs),
            command=command,
            outputs=outputs,
            discovery_roots=discovery_roots,
            initial_files_by_root=initial_files_by_root,
            exit_code=exit_code,
        )

    async def _run_command(
        self,
        *,
        command: list[str],
        stdout_path: Path,
        stderr_path: Path,
        cwd: Path,
    ) -> int:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=str(cwd),
            )
            return await process.wait()

    def _format_success(self, outputs: dict[str, Any]) -> str:
        lines = [f"{self.name} completed successfully."]
        output_lines = _format_output_lines(outputs)
        if output_lines:
            lines.extend(["", "Outputs:", *output_lines])
        summary_preview = _summary_preview(outputs)
        if summary_preview:
            lines.extend(["", "Summary preview:", summary_preview])
        return "\n".join(lines)


def _format_output_lines(outputs: dict[str, Any], limit: int = 16) -> list[str]:
    lines: list[str] = []
    for key, value in sorted(outputs.items()):
        if _looks_like_artifact_key(key):
            lines.append(f"- {key}: {value}")
            if len(lines) >= limit:
                return lines
    return lines


def _looks_like_artifact_key(key: str) -> bool:
    return (
        key.endswith("_path")
        or key.endswith("_prefix")
        or key.endswith("_dir")
        or key in {"output_path", "csv_path", "result_prefix"}
    )


def _summary_preview(outputs: dict[str, Any], max_chars: int = 4000) -> str:
    summary_path = outputs.get("summary_path")
    if not summary_path:
        return ""
    path = Path(str(summary_path))
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return ""
    return "\n".join(text.splitlines()[:20])[:max_chars].strip()


def _read_tail(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-max_chars:].strip()


def _discovery_roots_from_outputs(
    outputs: dict[str, Any],
    *,
    fallback: Path,
) -> list[Path]:
    output_dir = _metadata_path(outputs.get("output_dir"))
    if output_dir is not None:
        return [output_dir]

    special_dirs = [
        path
        for key in ("bed_dir", "grm_dir", "result_dir")
        if (path := _metadata_path(outputs.get(key))) is not None
    ]
    if special_dirs:
        return _dedupe_paths(special_dirs)

    file_parent_roots = [
        path.parent
        for key in ("stats_path", "summary_path")
        if (path := _metadata_path(outputs.get(key))) is not None
    ]
    if file_parent_roots:
        return _dedupe_paths(file_parent_roots)

    return [fallback]


def _metadata_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    return Path(str(value))


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        candidate = path.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(path)
    return unique


def _snapshot_files(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
