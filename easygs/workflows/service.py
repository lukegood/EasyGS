"""Persistent background agentic workflow service."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import contextmanager
import inspect
import json
import os
import re
import signal
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterator, TYPE_CHECKING

from loguru import logger

from easygs.bus.events import OutboundMessage
from easygs.bus.queue import MessageBus
from easygs.workflows.schema import (
    WorkflowActionRecord,
    WorkflowArtifactRecord,
    WorkflowRecord,
)

if TYPE_CHECKING:
    from easygs.agent.tools.registry import ToolRegistry
    from easygs.providers.base import LLMProvider, ToolCallRequest


_WORKFLOW_STATUS_FILTERS = {
    "all",
    "queued",
    "running",
    "waiting_user",
    "succeeded",
    "failed",
    "cancelled",
}
_ARTIFACT_KEY_RE = re.compile(r"(_path|_prefix|_dir)$")
_SYSTEM_ACTION_FILES = {"stdout.log", "stderr.log", "result.txt"}
_INTERRUPTED_ERROR = "Interrupted because EasyGS restarted before the workflow completed."
_CANCELLED_ERROR = "Cancelled by user."


def _now_ms() -> int:
    return int(time.time() * 1000)


def _fmt_ms(ts_ms: int | None) -> str:
    if not ts_ms:
        return "n/a"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_ms / 1000))


def _json_dict(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _json_list(text: str | None) -> list[str]:
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _safe_name(value: str, default: str = "workflow") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", (value or "").strip()).strip("._-")
    return text[:80] or default


class WorkflowService:
    """Queue, persist, and execute background agentic workflows."""

    def __init__(
        self,
        *,
        store_path: Path,
        bus: MessageBus,
        workspace: Path,
        provider: "LLMProvider | None" = None,
        tool_registry_factory: Callable[[WorkflowRecord], "ToolRegistry"] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_iterations: int = 40,
        mark_interrupted: bool = True,
        default_completion_notify_to: str | None = None,
        smtp_notifier: Any | None = None,
        process_termination_grace_seconds: float = 5.0,
    ):
        self.store_path = store_path
        self.db_path = self._resolve_db_path(store_path)
        self.bus = bus
        self.workspace = workspace
        self.provider = provider
        self.tool_registry_factory = tool_registry_factory
        self.model = model
        self.temperature = temperature
        self.max_iterations = max_iterations
        self._default_completion_notify_to = (default_completion_notify_to or "").strip().lower()
        self.smtp_notifier = smtp_notifier
        self.process_termination_grace_seconds = max(0.0, float(process_termination_grace_seconds))
        self._running = False
        self._worker_task: asyncio.Task[None] | None = None
        self._init_db()
        if mark_interrupted:
            self._mark_interrupted_workflows()

    @property
    def root_dir(self) -> Path:
        return self.db_path.parent

    @property
    def runs_dir(self) -> Path:
        return self.root_dir / "runs"

    def generate_workflow_id(self) -> str:
        return f"wf_{str(uuid.uuid4())[:8]}"

    async def start(self) -> None:
        if self._running and self._worker_task and not self._worker_task.done():
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._run_worker())
        logger.info("Agentic workflow worker started")

    def stop(self) -> None:
        self._running = False
        for workflow_id in self._running_workflow_ids():
            self._terminate_workflow_processes_sync(
                workflow_id,
                reason=_INTERRUPTED_ERROR,
                grace_seconds=self.process_termination_grace_seconds,
            )
        if self._worker_task:
            self._worker_task.cancel()
            self._worker_task = None
        logger.info("Agentic workflow worker stopping")

    async def submit_workflow(
        self,
        *,
        request: str,
        name: str | None = None,
        origin_channel: str | None,
        origin_chat_id: str | None,
        notify_on_completion: bool = True,
        output_dir: str | None = None,
        plan_summary: str | None = None,
        planned_steps: list[str] | None = None,
        expected_outputs: list[str] | None = None,
    ) -> WorkflowRecord:
        request_text = str(request or "").strip()
        if not request_text:
            raise ValueError("workflow request must not be empty.")

        workflow_id = self.generate_workflow_id()
        now = _now_ms()
        requested_work_dir = self._normalize_output_dir(output_dir)
        work_dir = Path(requested_work_dir) if requested_work_dir else self.runs_dir / workflow_id
        work_dir.mkdir(parents=True, exist_ok=True)

        display_name = (name or "").strip() or request_text[:80].strip() or workflow_id
        state = {
            "messages": self._initial_messages(
                request=request_text,
                workflow_id=workflow_id,
                work_dir=work_dir,
            ),
            "artifacts": [],
            "submission": {
                "plan_summary": (plan_summary or "").strip(),
                "planned_steps": [str(step).strip() for step in (planned_steps or []) if str(step).strip()],
                "expected_outputs": [str(item).strip() for item in (expected_outputs or []) if str(item).strip()],
            },
        }
        record = WorkflowRecord(
            id=workflow_id,
            name=display_name,
            status="queued",
            request=request_text,
            state=state,
            origin_channel=origin_channel,
            origin_chat_id=origin_chat_id,
            notify_on_completion=notify_on_completion,
            work_dir=str(work_dir),
            created_at_ms=now,
            updated_at_ms=now,
        )
        self._write_state(record)
        self._insert_workflow(record)
        await self.start()
        return record

    def get_workflow(self, workflow_id: str) -> WorkflowRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM workflows WHERE id = ?",
                (workflow_id,),
            ).fetchone()
        return self._row_to_workflow(row)

    def list_workflows(self) -> list[WorkflowRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workflows ORDER BY created_at_ms DESC",
            ).fetchall()
        return [wf for row in rows if (wf := self._row_to_workflow(row)) is not None]

    def get_actions(self, workflow_id: str) -> list[WorkflowActionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_actions WHERE workflow_id = ? ORDER BY idx ASC",
                (workflow_id,),
            ).fetchall()
        return [action for row in rows if (action := self._row_to_action(row)) is not None]

    def get_artifacts(self, workflow_id: str) -> list[WorkflowArtifactRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_artifacts WHERE workflow_id = ? ORDER BY artifact_id ASC",
                (workflow_id,),
            ).fetchall()
        return [artifact for row in rows if (artifact := self._row_to_artifact(row)) is not None]

    def find_active_for_origin(self, origin_channel: str, origin_chat_id: str) -> WorkflowRecord | None:
        """Return the newest active workflow associated with a chat origin."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM workflows
                WHERE origin_channel = ?
                  AND origin_chat_id = ?
                  AND status IN ('queued', 'running', 'waiting_user')
                ORDER BY created_at_ms DESC
                LIMIT 1
                """,
                (origin_channel, origin_chat_id),
            ).fetchone()
        return self._row_to_workflow(row)

    def add_user_message(self, workflow_id: str, content: str) -> bool:
        """Append a user message to a running workflow inbox."""
        workflow = self.get_workflow(workflow_id)
        if not workflow or workflow.status not in {"queued", "running", "waiting_user"}:
            return False
        message_id = f"wm_{str(uuid.uuid4())[:10]}"
        now = _now_ms()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_messages (
                    id, workflow_id, role, content, created_at_ms, consumed_at_ms
                ) VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (message_id, workflow_id, "user", str(content), now),
            )
        return True

    async def cancel_workflow(self, workflow_id: str, reason: str | None = None) -> str:
        """Cancel an active workflow and terminate any recorded child processes."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return f"Error: Workflow `{workflow_id}` not found."
        if workflow.status in {"succeeded", "failed", "cancelled"}:
            return f"Workflow `{workflow.id}` already finished with status `{workflow.status}`."
        message = self._cancel_reason(reason)
        now = _now_ms()
        updated = False
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE workflows
                SET status = ?, current_step_id = NULL, error = ?,
                    updated_at_ms = ?, completed_at_ms = ?
                WHERE id = ? AND status IN ('queued', 'running', 'waiting_user')
                """,
                ("cancelled", message, now, now, workflow.id),
            )
            updated = cursor.rowcount > 0
            if updated:
                conn.execute(
                    """
                    UPDATE workflow_actions
                    SET status = ?, error = ?, completed_at_ms = ?
                    WHERE workflow_id = ? AND status = 'running'
                    """,
                    ("cancelled", message, now, workflow.id),
                )

        if not updated:
            refreshed = self.get_workflow(workflow.id)
            status = refreshed.status if refreshed else "unknown"
            return f"Workflow `{workflow.id}` already finished with status `{status}`."

        await self._terminate_workflow_processes(
            workflow.id,
            reason=message,
            grace_seconds=self.process_termination_grace_seconds,
        )
        return f"Workflow `{workflow.id}` cancelled."

    def drain_user_messages(self, workflow_id: str) -> list[dict[str, Any]]:
        """Return and mark unconsumed user messages for a workflow."""
        now = _now_ms()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at_ms
                FROM workflow_messages
                WHERE workflow_id = ? AND consumed_at_ms IS NULL
                ORDER BY created_at_ms ASC
                """,
                (workflow_id,),
            ).fetchall()
            if rows:
                conn.executemany(
                    "UPDATE workflow_messages SET consumed_at_ms = ? WHERE id = ?",
                    [(now, row["id"]) for row in rows],
                )
        return [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "created_at_ms": row["created_at_ms"],
            }
            for row in rows
        ]

    def format_status(self, workflow_id: str) -> str:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return f"Error: Workflow `{workflow_id}` not found."

        lines = [
            f"Workflow `{workflow.id}`",
            f"- Name: {workflow.name}",
            f"- Status: {workflow.status}",
            f"- Created: {_fmt_ms(workflow.created_at_ms)}",
            f"- Started: {_fmt_ms(workflow.started_at_ms)}",
            f"- Completed: {_fmt_ms(workflow.completed_at_ms)}",
            f"- Current action: {workflow.current_action_id or 'n/a'}",
            f"- Iterations: {workflow.iteration_count}",
            f"- Work dir: {workflow.work_dir}",
            "",
            "Actions",
        ]
        actions = self.get_actions(workflow.id)
        if not actions:
            lines.append("- none yet")
        for action in actions:
            suffix = f" | exit code {action.exit_code}" if action.exit_code is not None else ""
            lines.append(f"- {action.idx}. {action.action_id} | {action.tool_name} | {action.status}{suffix}")
            if action.error:
                lines.append(f"  Error: {action.error}")
        if workflow.error:
            lines.extend(["", f"Error: {workflow.error}"])
        return "\n".join(lines)

    def format_result(self, workflow_id: str) -> str:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return f"Error: Workflow `{workflow_id}` not found."
        if workflow.status in {"queued", "running", "waiting_user"}:
            return (
                f"Workflow `{workflow.id}` is still {workflow.status}.\n"
                "Use `get_workflow_status` to check progress again later."
            )

        lines = [
            f"Workflow `{workflow.id}` finished with status `{workflow.status}`.",
            f"- Name: {workflow.name}",
            f"- Work dir: {workflow.work_dir}",
        ]
        if workflow.final_summary:
            lines.extend(["", "Final summary:", workflow.final_summary])
        if workflow.error:
            lines.append(f"- Error: {workflow.error}")

        artifacts = self.get_artifacts(workflow.id)
        if artifacts:
            lines.extend(["", "Artifacts"])
            for artifact in artifacts[:24]:
                lines.append(f"- {artifact.name}: {artifact.value}")

        actions = self.get_actions(workflow.id)
        if actions:
            lines.extend(["", "Action logs"])
            for action in actions:
                lines.append(f"- {action.idx}. {action.tool_name}: {action.status}")
                if action.result_path:
                    lines.append(f"  - Result: {action.result_path}")
                if action.stdout_path:
                    lines.append(f"  - Stdout: {action.stdout_path}")
                if action.stderr_path:
                    lines.append(f"  - Stderr: {action.stderr_path}")
        return "\n".join(lines)

    def format_listing(self, *, status: str = "all", limit: int = 20) -> str:
        workflows = self.list_workflows()
        normalized = (status or "all").strip().lower()
        if normalized not in _WORKFLOW_STATUS_FILTERS:
            allowed = ", ".join(sorted(_WORKFLOW_STATUS_FILTERS))
            return f"Error: status must be one of: {allowed}"
        if limit <= 0:
            return "Error: limit must be greater than 0"

        counts = {name: 0 for name in ("queued", "running", "waiting_user", "succeeded", "failed", "cancelled")}
        for workflow in workflows:
            if workflow.status in counts:
                counts[workflow.status] += 1
        filtered = workflows if normalized == "all" else [
            workflow for workflow in workflows if workflow.status == normalized
        ]

        lines = [
            "Background workflows",
            f"- Total: {len(workflows)}",
            f"- Queued: {counts['queued']}",
            f"- Running: {counts['running']}",
            f"- Waiting user: {counts['waiting_user']}",
            f"- Succeeded: {counts['succeeded']}",
            f"- Failed: {counts['failed']}",
            f"- Cancelled: {counts['cancelled']}",
            f"- Filter: {normalized}",
        ]
        if not filtered:
            lines.append("- Matching workflows: 0")
            return "\n".join(lines)

        lines.append(f"- Matching workflows: {len(filtered)} (showing up to {limit})")
        for workflow in filtered[:limit]:
            current = workflow.current_action_id or "n/a"
            lines.append(
                f"- {workflow.id} | {workflow.status} | {workflow.name} | "
                f"current {current} | created {_fmt_ms(workflow.created_at_ms)}"
            )
        return "\n".join(lines)

    def format_capabilities(self) -> str:
        if not self.tool_registry_factory:
            return "Workflow capabilities are unavailable because no tool registry factory is configured."
        dummy = WorkflowRecord(id="wf_preview", name="preview", work_dir=str(self.workspace), request="")
        registry = self.tool_registry_factory(dummy)
        names = sorted(
            name for name in registry.tool_names
            if name not in {"message", "spawn_agent", "submit_workflow"}
        )
        lines = ["Workflow action capabilities"]
        lines.extend(f"- {name}" for name in names)
        return "\n".join(lines)

    def _normalize_output_dir(self, output_dir: str | None) -> str:
        candidate = str(output_dir or "").strip()
        if not candidate:
            return ""
        return str(Path(candidate).expanduser().resolve())

    def _cancel_reason(self, reason: str | None) -> str:
        detail = str(reason or "").strip()
        return f"{_CANCELLED_ERROR} {detail}".strip()

    def _workflow_cancelled(self, workflow_id: str) -> bool:
        workflow = self.get_workflow(workflow_id)
        return bool(workflow and workflow.status == "cancelled")

    def _workflow_cancel_message(self, workflow_id: str) -> str:
        workflow = self.get_workflow(workflow_id)
        if workflow and workflow.error:
            return workflow.error
        return self._cancel_reason(None)

    def _resolve_db_path(self, store_path: Path) -> Path:
        return store_path if store_path.suffix == ".db" else store_path.with_suffix(".db")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    origin_channel TEXT,
                    origin_chat_id TEXT,
                    notify_on_completion INTEGER NOT NULL,
                    work_dir TEXT NOT NULL,
                    current_step_id TEXT,
                    created_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    started_at_ms INTEGER,
                    completed_at_ms INTEGER,
                    error TEXT
                )
                """
            )
            self._ensure_column(conn, "workflows", "final_summary", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "workflows", "iteration_count", "INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_actions (
                    workflow_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    iteration INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    tool_call_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    args_json TEXT NOT NULL,
                    result_preview TEXT NOT NULL,
                    outputs_json TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    stdout_path TEXT NOT NULL,
                    stderr_path TEXT NOT NULL,
                    result_path TEXT NOT NULL,
                    started_at_ms INTEGER,
                    completed_at_ms INTEGER,
                    exit_code INTEGER,
                    error TEXT,
                    PRIMARY KEY (workflow_id, action_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_artifacts (
                    workflow_id TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    producer_action_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    value TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (workflow_id, artifact_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_messages (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    consumed_at_ms INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_processes (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    pgid INTEGER,
                    command_json TEXT NOT NULL,
                    cwd TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at_ms INTEGER NOT NULL,
                    completed_at_ms INTEGER,
                    exit_code INTEGER,
                    termination_reason TEXT,
                    error TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_created_at ON workflows(created_at_ms DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_actions_workflow ON workflow_actions(workflow_id, idx)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_artifacts_workflow ON workflow_artifacts(workflow_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_messages_workflow ON workflow_messages(workflow_id, consumed_at_ms)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_processes_workflow ON workflow_processes(workflow_id, status)")

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if any(row["name"] == column for row in rows):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _insert_workflow(self, workflow: WorkflowRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflows (
                    id, name, status, request, plan_json, origin_channel,
                    origin_chat_id, notify_on_completion, work_dir, current_step_id,
                    created_at_ms, updated_at_ms, started_at_ms, completed_at_ms,
                    error, final_summary, iteration_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._workflow_values(workflow),
            )

    def _update_workflow(self, workflow: WorkflowRecord) -> None:
        workflow.updated_at_ms = _now_ms()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflows
                SET name = ?, status = ?, request = ?, plan_json = ?,
                    origin_channel = ?, origin_chat_id = ?, notify_on_completion = ?,
                    work_dir = ?, current_step_id = ?, created_at_ms = ?,
                    updated_at_ms = ?, started_at_ms = ?, completed_at_ms = ?,
                    error = ?, final_summary = ?, iteration_count = ?
                WHERE id = ?
                  AND NOT (
                    status IN ('succeeded', 'failed', 'cancelled')
                    AND status != ?
                  )
                """,
                self._workflow_values(workflow)[1:] + (workflow.id, workflow.status),
            )

    def _workflow_values(self, workflow: WorkflowRecord) -> tuple[Any, ...]:
        return (
            workflow.id,
            workflow.name,
            workflow.status,
            workflow.request,
            json.dumps(workflow.state, ensure_ascii=False),
            workflow.origin_channel,
            workflow.origin_chat_id,
            int(workflow.notify_on_completion),
            workflow.work_dir,
            workflow.current_action_id,
            workflow.created_at_ms,
            workflow.updated_at_ms,
            workflow.started_at_ms,
            workflow.completed_at_ms,
            workflow.error,
            workflow.final_summary,
            workflow.iteration_count,
        )

    def _row_to_workflow(self, row: sqlite3.Row | None) -> WorkflowRecord | None:
        if row is None:
            return None
        return WorkflowRecord(
            id=row["id"],
            name=row["name"],
            status=row["status"],
            request=row["request"],
            state=_json_dict(row["plan_json"]),
            origin_channel=row["origin_channel"],
            origin_chat_id=row["origin_chat_id"],
            notify_on_completion=bool(row["notify_on_completion"]),
            work_dir=row["work_dir"],
            current_action_id=row["current_step_id"],
            created_at_ms=row["created_at_ms"],
            updated_at_ms=row["updated_at_ms"],
            started_at_ms=row["started_at_ms"],
            completed_at_ms=row["completed_at_ms"],
            error=row["error"],
            final_summary=row["final_summary"],
            iteration_count=row["iteration_count"],
        )

    def _insert_action(self, action: WorkflowActionRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_actions (
                    workflow_id, action_id, idx, iteration, tool_name, tool_call_id,
                    status, args_json, result_preview, outputs_json, command_json,
                    stdout_path, stderr_path, result_path, started_at_ms,
                    completed_at_ms, exit_code, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._action_values(action),
            )

    def _update_action(self, action: WorkflowActionRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_actions
                SET idx = ?, iteration = ?, tool_name = ?, tool_call_id = ?,
                    status = ?, args_json = ?, result_preview = ?, outputs_json = ?,
                    command_json = ?, stdout_path = ?, stderr_path = ?, result_path = ?,
                    started_at_ms = ?, completed_at_ms = ?, exit_code = ?, error = ?
                WHERE workflow_id = ? AND action_id = ?
                  AND NOT (
                    status IN ('succeeded', 'failed', 'cancelled')
                    AND status != ?
                  )
                """,
                self._action_values(action)[2:] + (
                    action.workflow_id,
                    action.action_id,
                    action.status,
                ),
            )

    def _action_values(self, action: WorkflowActionRecord) -> tuple[Any, ...]:
        return (
            action.workflow_id,
            action.action_id,
            action.idx,
            action.iteration,
            action.tool_name,
            action.tool_call_id,
            action.status,
            json.dumps(action.args, ensure_ascii=False),
            action.result_preview,
            json.dumps(action.outputs, ensure_ascii=False),
            json.dumps(action.command, ensure_ascii=False),
            action.stdout_path,
            action.stderr_path,
            action.result_path,
            action.started_at_ms,
            action.completed_at_ms,
            action.exit_code,
            action.error,
        )

    def _row_to_action(self, row: sqlite3.Row | None) -> WorkflowActionRecord | None:
        if row is None:
            return None
        return WorkflowActionRecord(
            workflow_id=row["workflow_id"],
            action_id=row["action_id"],
            idx=row["idx"],
            iteration=row["iteration"],
            tool_name=row["tool_name"],
            tool_call_id=row["tool_call_id"],
            status=row["status"],
            args=_json_dict(row["args_json"]),
            result_preview=row["result_preview"],
            outputs=_json_dict(row["outputs_json"]),
            command=_json_list(row["command_json"]),
            stdout_path=row["stdout_path"],
            stderr_path=row["stderr_path"],
            result_path=row["result_path"],
            started_at_ms=row["started_at_ms"],
            completed_at_ms=row["completed_at_ms"],
            exit_code=row["exit_code"],
            error=row["error"],
        )

    def _insert_artifact(self, artifact: WorkflowArtifactRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO workflow_artifacts (
                    workflow_id, artifact_id, producer_action_id, name, kind,
                    value, summary, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.workflow_id,
                    artifact.artifact_id,
                    artifact.producer_action_id,
                    artifact.name,
                    artifact.kind,
                    artifact.value,
                    artifact.summary,
                    json.dumps(artifact.metadata, ensure_ascii=False),
                ),
            )

    def _row_to_artifact(self, row: sqlite3.Row | None) -> WorkflowArtifactRecord | None:
        if row is None:
            return None
        return WorkflowArtifactRecord(
            workflow_id=row["workflow_id"],
            artifact_id=row["artifact_id"],
            producer_action_id=row["producer_action_id"],
            name=row["name"],
            kind=row["kind"],
            value=row["value"],
            summary=row["summary"],
            metadata=_json_dict(row["metadata_json"]),
        )

    def _insert_process(
        self,
        *,
        process_id: str,
        workflow_id: str,
        action_id: str,
        pid: int,
        pgid: int | None,
        command: list[str],
        cwd: Path,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workflow_processes (
                    id, workflow_id, action_id, pid, pgid, command_json, cwd,
                    status, started_at_ms, completed_at_ms, exit_code,
                    termination_reason, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL)
                """,
                (
                    process_id,
                    workflow_id,
                    action_id,
                    pid,
                    pgid,
                    json.dumps(command, ensure_ascii=False),
                    str(cwd),
                    "running",
                    _now_ms(),
                ),
            )

    def _finish_process(
        self,
        process_id: str,
        *,
        status: str,
        exit_code: int | None = None,
        termination_reason: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_processes
                SET status = ?, completed_at_ms = ?, exit_code = ?,
                    termination_reason = COALESCE(?, termination_reason),
                    error = COALESCE(?, error)
                WHERE id = ? AND status = 'running'
                """,
                (status, _now_ms(), exit_code, termination_reason, error, process_id),
            )

    def _running_process_rows(self, workflow_id: str) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT id, pid, pgid
                FROM workflow_processes
                WHERE workflow_id = ? AND status = 'running'
                """,
                (workflow_id,),
            ).fetchall()

    def _running_workflow_ids(self) -> list[str]:
        with self._connect() as conn:
            return [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM workflows WHERE status = 'running'"
                ).fetchall()
            ]

    async def _terminate_workflow_processes(
        self,
        workflow_id: str,
        *,
        reason: str,
        grace_seconds: float = 5.0,
    ) -> None:
        rows = self._running_process_rows(workflow_id)
        if not rows:
            logger.info("No recorded running workflow processes to terminate for {}", workflow_id)
            return
        logger.info("Terminating {} recorded workflow process(es) for {}", len(rows), workflow_id)
        for row in rows:
            self._signal_process_row(row, signal.SIGTERM)
        await asyncio.sleep(grace_seconds)
        for row in rows:
            if self._process_row_alive(row):
                self._signal_process_row(row, signal.SIGKILL)
        self._mark_process_rows_terminated(workflow_id, reason)

    def _terminate_workflow_processes_sync(
        self,
        workflow_id: str,
        *,
        reason: str,
        grace_seconds: float = 2.0,
    ) -> None:
        rows = self._running_process_rows(workflow_id)
        if not rows:
            logger.info("No recorded running workflow processes to terminate for {}", workflow_id)
            return
        logger.info("Terminating {} recorded workflow process(es) for {}", len(rows), workflow_id)
        for row in rows:
            self._signal_process_row(row, signal.SIGTERM)
        time.sleep(grace_seconds)
        for row in rows:
            if self._process_row_alive(row):
                self._signal_process_row(row, signal.SIGKILL)
        self._mark_process_rows_terminated(workflow_id, reason)

    def _mark_process_rows_terminated(self, workflow_id: str, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflow_processes
                SET status = ?, completed_at_ms = ?, termination_reason = ?
                WHERE workflow_id = ? AND status = 'running'
                """,
                ("terminated", _now_ms(), reason, workflow_id),
            )

    def _signal_process_row(self, row: sqlite3.Row, sig: signal.Signals) -> None:
        pid = int(row["pid"])
        pgid = row["pgid"]
        try:
            if pgid:
                os.killpg(int(pgid), sig)
            else:
                os.kill(pid, sig)
        except ProcessLookupError:
            self._finish_process(row["id"], status="exited")
        except PermissionError as exc:
            self._finish_process(row["id"], status="kill_failed", error=str(exc))

    def _process_row_alive(self, row: sqlite3.Row) -> bool:
        if self._process_record_closed(row["id"]):
            return False
        pid = int(row["pid"])
        pgid = row["pgid"]
        try:
            if pgid:
                os.killpg(int(pgid), 0)
            else:
                os.kill(pid, 0)
            return True
        except ProcessLookupError:
            self._finish_process(row["id"], status="exited")
            return False
        except PermissionError:
            return True

    def _process_record_closed(self, process_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM workflow_processes WHERE id = ?",
                (process_id,),
            ).fetchone()
        return bool(row and row["status"] != "running")

    async def _run_action_command(
        self,
        *,
        workflow_id: str,
        action_id: str,
        command: list[str],
        stdout_path: Path,
        stderr_path: Path,
        cwd: Path,
    ) -> int:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        process_id = f"wp_{str(uuid.uuid4())[:10]}"
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=str(cwd),
                start_new_session=True,
            )
            try:
                pgid = os.getpgid(process.pid)
            except OSError:
                pgid = None
            self._insert_process(
                process_id=process_id,
                workflow_id=workflow_id,
                action_id=action_id,
                pid=process.pid,
                pgid=pgid,
                command=command,
                cwd=cwd,
            )
            try:
                exit_code = await process.wait()
            except asyncio.CancelledError:
                self._signal_process_row(
                    {
                        "id": process_id,
                        "pid": process.pid,
                        "pgid": pgid,
                    },
                    signal.SIGTERM,
                )
                raise
        status = "terminated" if self._workflow_cancelled(workflow_id) else "exited"
        self._finish_process(process_id, status=status, exit_code=exit_code)
        return exit_code

    def _mark_interrupted_workflows(self) -> None:
        now = _now_ms()
        for workflow_id in self._running_workflow_ids():
            self._terminate_workflow_processes_sync(
                workflow_id,
                reason=_INTERRUPTED_ERROR,
                grace_seconds=self.process_termination_grace_seconds,
            )
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE workflows
                SET status = ?, error = ?, updated_at_ms = ?, completed_at_ms = ?
                WHERE status = 'running'
                """,
                (
                    "failed",
                    _INTERRUPTED_ERROR,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                UPDATE workflow_actions
                SET status = ?, error = ?, completed_at_ms = ?
                WHERE status = 'running'
                """,
                (
                    "failed",
                    _INTERRUPTED_ERROR,
                    now,
                ),
            )

    async def _run_worker(self) -> None:
        while self._running:
            try:
                workflow_id = self._claim_next_queued_workflow()
                if not workflow_id:
                    await asyncio.sleep(1)
                    continue
                await self._run_workflow(workflow_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Workflow worker error: {}", exc)
                await asyncio.sleep(1)

    def _claim_next_queued_workflow(self) -> str | None:
        now = _now_ms()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            running = conn.execute(
                "SELECT id FROM workflows WHERE status = 'running' LIMIT 1"
            ).fetchone()
            if running:
                conn.commit()
                return None
            row = conn.execute(
                """
                SELECT id FROM workflows
                WHERE status = 'queued'
                ORDER BY created_at_ms ASC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                conn.commit()
                return None
            workflow_id = row["id"]
            conn.execute(
                """
                UPDATE workflows
                SET status = ?, started_at_ms = ?, updated_at_ms = ?
                WHERE id = ?
                """,
                ("running", now, now, workflow_id),
            )
            conn.commit()
            return workflow_id

    async def _run_workflow(self, workflow_id: str) -> None:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return
        if not self.provider or not self.tool_registry_factory:
            workflow.status = "failed"
            workflow.error = "Workflow service is not configured with an LLM provider and tools."
            workflow.completed_at_ms = _now_ms()
            self._update_workflow(workflow)
            await self._announce_completion(workflow)
            return

        workflow.status = "running"
        workflow.error = None
        workflow.started_at_ms = workflow.started_at_ms or _now_ms()
        self._update_workflow(workflow)
        registry = self.tool_registry_factory(workflow)
        messages = self._state_messages(workflow)

        logger.info("Workflow [{}] starting: {}", workflow.id, workflow.name)
        try:
            for iteration in range(workflow.iteration_count + 1, self.max_iterations + 1):
                if self._workflow_cancelled(workflow.id):
                    workflow = self.get_workflow(workflow.id) or workflow
                    break
                if self._append_pending_user_messages(workflow, messages):
                    self._save_messages(workflow, messages)
                workflow.iteration_count = iteration
                self._update_workflow(workflow)
                response = await self.provider.chat(
                    messages=messages,
                    tools=registry.get_definitions(),
                    model=self.model,
                    temperature=self.temperature,
                )

                if response.has_tool_calls:
                    if self._workflow_cancelled(workflow.id):
                        workflow = self.get_workflow(workflow.id) or workflow
                        break
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                    assistant_msg: dict[str, Any] = {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": tool_call_dicts,
                    }
                    if response.reasoning_content:
                        assistant_msg["reasoning_content"] = response.reasoning_content
                    messages.append(assistant_msg)

                    for tool_call in response.tool_calls:
                        result = await self._execute_tool_action(
                            workflow=workflow,
                            registry=registry,
                            tool_call=tool_call,
                            iteration=iteration,
                        )
                        if self._workflow_cancelled(workflow.id):
                            workflow = self.get_workflow(workflow.id) or workflow
                            break
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_call.name,
                                "content": result,
                            }
                        )
                        if self._append_pending_user_messages(workflow, messages):
                            self._save_messages(workflow, messages)
                    if self._workflow_cancelled(workflow.id):
                        break

                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Based on the action results, available artifacts, and any user messages "
                                "added to this workflow, either choose the next workflow action or provide "
                                "the final workflow summary."
                            ),
                        }
                    )
                    self._save_messages(workflow, messages)
                    continue

                if self._workflow_cancelled(workflow.id):
                    workflow = self.get_workflow(workflow.id) or workflow
                    break
                final_summary = (response.content or "").strip()
                workflow.status = "succeeded"
                workflow.current_action_id = None
                workflow.final_summary = final_summary or "Workflow completed."
                workflow.completed_at_ms = _now_ms()
                workflow.error = None
                messages.append({"role": "assistant", "content": workflow.final_summary})
                self._save_messages(workflow, messages)
                self._update_workflow(workflow)
                break
            else:
                if self._workflow_cancelled(workflow.id):
                    workflow = self.get_workflow(workflow.id) or workflow
                else:
                    workflow.status = "failed"
                    workflow.current_action_id = None
                    workflow.completed_at_ms = _now_ms()
                    workflow.error = f"Reached max workflow iterations ({self.max_iterations})."
                    self._save_messages(workflow, messages)
                    self._update_workflow(workflow)
        except Exception as exc:
            if self._workflow_cancelled(workflow.id):
                workflow = self.get_workflow(workflow.id) or workflow
            else:
                workflow.status = "failed"
                workflow.current_action_id = None
                workflow.completed_at_ms = _now_ms()
                workflow.error = str(exc)
                self._save_messages(workflow, messages)
                self._update_workflow(workflow)
                logger.error("Workflow [{}] failed: {}", workflow.id, exc)

        await self._announce_completion(workflow)
        logger.info("Workflow [{}] completed with status {}", workflow.id, workflow.status)

    async def _execute_tool_action(
        self,
        *,
        workflow: WorkflowRecord,
        registry: "ToolRegistry",
        tool_call: "ToolCallRequest",
        iteration: int,
    ) -> str:
        idx = len(self.get_actions(workflow.id)) + 1
        action_id = f"act_{idx:03d}_{_safe_name(tool_call.name, 'tool')}"
        action_dir = self._action_dir(workflow, action_id)
        stdout_path = action_dir / "stdout.log"
        stderr_path = action_dir / "stderr.log"
        result_path = action_dir / "result.txt"
        default_output_dir = action_dir
        action = WorkflowActionRecord(
            workflow_id=workflow.id,
            action_id=action_id,
            idx=idx,
            iteration=iteration,
            tool_name=tool_call.name,
            tool_call_id=tool_call.id,
            status="running",
            args=dict(tool_call.arguments or {}),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            result_path=str(result_path),
            started_at_ms=_now_ms(),
        )
        action_dir.mkdir(parents=True, exist_ok=True)
        default_discovery_roots = [default_output_dir]
        initial_files_by_root = {
            default_output_dir: self._snapshot_action_files(default_output_dir)
        }
        self._insert_action(action)
        workflow.current_action_id = action_id
        self._update_workflow(workflow)

        tool = registry.get(tool_call.name)
        from easygs.agent.tools.workflow import WorkflowActionResult

        try:
            if tool is None:
                result = WorkflowActionResult(
                    content=f"Error: Tool '{tool_call.name}' not found.",
                    error=f"Tool '{tool_call.name}' not found.",
                )
            else:
                execute_workflow_action = getattr(tool, "execute_workflow_action", None)
                if callable(execute_workflow_action):
                    action_kwargs = {
                        "args": dict(tool_call.arguments or {}),
                        "action_dir": action_dir,
                        "stdout_path": stdout_path,
                        "stderr_path": stderr_path,
                    }
                    if self._accepts_keyword(execute_workflow_action, "default_output_dir"):
                        action_kwargs["default_output_dir"] = default_output_dir
                    if self._accepts_keyword(execute_workflow_action, "command_runner"):
                        action_kwargs["command_runner"] = (
                            lambda command, out, err, cwd: self._run_action_command(
                                workflow_id=workflow.id,
                                action_id=action_id,
                                command=command,
                                stdout_path=out,
                                stderr_path=err,
                                cwd=cwd,
                            )
                        )
                    result = await execute_workflow_action(**action_kwargs)
                else:
                    text = await registry.execute(tool_call.name, dict(tool_call.arguments or {}))
                    result = WorkflowActionResult(
                        content=text,
                        exit_code=0 if not text.startswith("Error:") else None,
                        error=text if text.startswith("Error:") else None,
                    )
                    stdout_path.write_text(text, encoding="utf-8")
                    stderr_path.write_text("", encoding="utf-8")

            if self._workflow_cancelled(workflow.id):
                message = self._workflow_cancel_message(workflow.id)
                result_path.write_text("Cancelled: " + message, encoding="utf-8")
                action.status = "cancelled"
                action.error = message
                action.result_preview = "Cancelled: " + message
                action.completed_at_ms = _now_ms()
                self._update_action(action)
                return "Cancelled: " + message

            result_path.write_text(result.content, encoding="utf-8")
            action.command = result.command
            action.outputs = dict(result.outputs or {})
            action.exit_code = result.exit_code
            action.error = result.error
            action.result_preview = result.content[:4000]
            action.status = "failed" if result.error else "succeeded"
            action.completed_at_ms = _now_ms()
            self._update_action(action)
            discovery_roots = result.discovery_roots or default_discovery_roots
            discovered_initial_files = result.initial_files_by_root or initial_files_by_root
            self._register_artifacts(
                workflow,
                action,
                discovery_roots=discovery_roots,
                initial_files_by_root=discovered_initial_files,
            )
            workflow.current_action_id = None
            self._update_workflow(workflow)
            return result.content
        except Exception as exc:
            error = str(exc)
            stderr_path.write_text(error + "\n", encoding="utf-8")
            result_path.write_text("Error: " + error, encoding="utf-8")
            action.status = "failed"
            action.error = error
            action.result_preview = "Error: " + error
            action.completed_at_ms = _now_ms()
            self._update_action(action)
            self._register_artifacts(
                workflow,
                action,
                discovery_roots=default_discovery_roots,
                initial_files_by_root=initial_files_by_root,
            )
            workflow.current_action_id = None
            self._update_workflow(workflow)
            return "Error: " + error

    def _register_artifacts(
        self,
        workflow: WorkflowRecord,
        action: WorkflowActionRecord,
        *,
        discovery_roots: list[Path],
        initial_files_by_root: dict[Path, set[str]],
    ) -> None:
        artifacts = list(workflow.state.get("artifacts") or [])
        explicit_file_values: set[Path] = set()
        for key, value in sorted(action.outputs.items()):
            if value in (None, ""):
                continue
            if not (_ARTIFACT_KEY_RE.search(key) or key in {"output_path", "csv_path", "result_prefix"}):
                continue
            artifact = WorkflowArtifactRecord(
                workflow_id=workflow.id,
                artifact_id=f"{action.action_id}_{key}",
                producer_action_id=action.action_id,
                name=key,
                kind=self._infer_artifact_kind(key, value),
                value=str(value),
                summary=f"Produced by {action.tool_name}",
                metadata={"tool_name": action.tool_name, "discovery": "metadata"},
            )
            self._insert_artifact(artifact)
            artifacts.append(
                {
                    "id": artifact.artifact_id,
                    "name": artifact.name,
                    "kind": artifact.kind,
                    "value": artifact.value,
                    "producer_action_id": artifact.producer_action_id,
                    "summary": artifact.summary,
                }
            )
            candidate = Path(str(value))
            if candidate.is_file():
                explicit_file_values.add(candidate.resolve())

        discovered = self._discover_action_artifacts(
            discovery_roots,
            initial_files_by_root=initial_files_by_root,
        )
        for idx, (discovery_root, path) in enumerate(discovered, start=1):
            if path.resolve() in explicit_file_values:
                continue
            relative_path = path.relative_to(discovery_root).as_posix()
            artifact = WorkflowArtifactRecord(
                workflow_id=workflow.id,
                artifact_id=f"{action.action_id}_discovered_{idx:03d}",
                producer_action_id=action.action_id,
                name=relative_path,
                kind="discovered_file",
                value=str(path),
                summary=f"Discovered after {action.tool_name}",
                metadata={
                    "tool_name": action.tool_name,
                    "relative_path": relative_path,
                    "discovery_root": str(discovery_root),
                    "size_bytes": path.stat().st_size,
                    "discovery": "action_dir",
                },
            )
            self._insert_artifact(artifact)
            artifacts.append(
                {
                    "id": artifact.artifact_id,
                    "name": artifact.name,
                    "kind": artifact.kind,
                    "value": artifact.value,
                    "producer_action_id": artifact.producer_action_id,
                    "summary": artifact.summary,
                }
            )
        workflow.state["artifacts"] = artifacts[-80:]
        self._write_state(workflow)
        self._update_workflow(workflow)

    def _action_dir(
        self,
        workflow: WorkflowRecord,
        action_id: str,
    ) -> Path:
        return Path(workflow.work_dir) / "actions" / action_id

    def _accepts_keyword(self, fn: Any, name: str) -> bool:
        try:
            signature = inspect.signature(fn)
        except (TypeError, ValueError):
            return False
        for parameter in signature.parameters.values():
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
        return name in signature.parameters

    def _snapshot_action_files(self, discovery_root: Path) -> set[str]:
        if not discovery_root.exists():
            return set()
        return {
            path.relative_to(discovery_root).as_posix()
            for path in discovery_root.rglob("*")
            if path.is_file()
        }

    def _discover_action_artifacts(
        self,
        discovery_roots: list[Path],
        *,
        initial_files_by_root: dict[Path, set[str]],
    ) -> list[tuple[Path, Path]]:
        discovered: list[tuple[Path, Path]] = []
        seen_paths: set[Path] = set()
        for discovery_root in discovery_roots:
            if not discovery_root.exists():
                continue
            initial_files = initial_files_by_root.get(discovery_root, set())
            for path in discovery_root.rglob("*"):
                if not path.is_file():
                    continue
                relative_path = path.relative_to(discovery_root)
                relative_text = relative_path.as_posix()
                if relative_text in initial_files:
                    continue
                if (
                    discovery_root.name.startswith("act_")
                    and len(relative_path.parts) == 1
                    and relative_path.name in _SYSTEM_ACTION_FILES
                ):
                    continue
                resolved = path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                discovered.append((discovery_root, path))
        return sorted(discovered, key=lambda item: (str(item[0]), str(item[1])))

    def _infer_artifact_kind(self, key: str, value: Any) -> str:
        lowered = key.lower()
        text = str(value).lower()
        if "vcf" in lowered or text.endswith((".vcf", ".vcf.gz")):
            return "genotype.vcf"
        if "bfile" in lowered or "bed_prefix" in lowered:
            return "genotype.plink_bfile"
        if text.endswith(".csv") or "csv" in lowered:
            return "table.csv"
        if text.endswith(".txt") or "summary" in lowered:
            return "text"
        if lowered.endswith("_dir"):
            return "directory"
        if lowered.endswith("_prefix") or "prefix" in lowered:
            return "prefix"
        return "file"

    def _initial_messages(
        self,
        *,
        request: str,
        workflow_id: str,
        work_dir: Path,
    ) -> list[dict[str, Any]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are the EasyGS background workflow agent. Complete the submitted scientific "
                    "analysis request by taking useful actions, inspecting outputs before dependent "
                    "decisions, incorporating any user messages added to this workflow, and finishing "
                    "with a concise final summary. "
                    "Use available files and generated artifacts as evidence. Do not submit another "
                    "background workflow from inside this workflow. Prefer workflow action tools for "
                    "analysis work. Keep outputs inside the workflow directory.\n\n"
                    f"Workflow ID: {workflow_id}\n"
                    f"Workflow directory: {work_dir}"
                ),
            },
            {"role": "user", "content": request},
        ]

    def _append_pending_user_messages(
        self,
        workflow: WorkflowRecord,
        messages: list[dict[str, Any]],
    ) -> bool:
        pending = self.drain_user_messages(workflow.id)
        if not pending:
            return False
        lines = [
            "New user messages arrived while this workflow was running.",
            "Treat them as current conversation context and adapt the plan when appropriate.",
            "If the user asks about progress, answer from the current workflow state, actions, and artifacts.",
            "",
        ]
        for item in pending:
            lines.append(f"- {_fmt_ms(item.get('created_at_ms'))}: {item.get('content', '')}")
        messages.append({"role": "user", "content": "\n".join(lines)})
        return True

    def _state_messages(self, workflow: WorkflowRecord) -> list[dict[str, Any]]:
        messages = workflow.state.get("messages")
        if isinstance(messages, list) and messages:
            return [msg for msg in messages if isinstance(msg, dict)]
        return self._initial_messages(
            request=workflow.request,
            workflow_id=workflow.id,
            work_dir=Path(workflow.work_dir),
        )

    def _save_messages(self, workflow: WorkflowRecord, messages: list[dict[str, Any]]) -> None:
        workflow.state["messages"] = messages
        self._write_state(workflow)
        self._update_workflow(workflow)

    def _write_state(self, workflow: WorkflowRecord) -> None:
        work_dir = Path(workflow.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "state.json").write_text(
            json.dumps(workflow.state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def _announce_completion(self, workflow: WorkflowRecord) -> None:
        if not workflow.notify_on_completion or not workflow.origin_channel or not workflow.origin_chat_id:
            return

        if workflow.status == "succeeded":
            status_text = "completed successfully"
        elif workflow.status == "cancelled":
            status_text = "was cancelled"
        else:
            status_text = "failed"
        lines = [
            f"[Background workflow '{workflow.name}' {status_text}]",
            "",
            f"Workflow ID: {workflow.id}",
            f"Status: {workflow.status}",
        ]
        if workflow.final_summary:
            lines.extend(["", "Final summary:", workflow.final_summary])
        artifacts = self.get_artifacts(workflow.id)
        if artifacts:
            lines.extend(["", "Artifacts:"])
            for artifact in artifacts[:12]:
                lines.append(f"- {artifact.name}: {artifact.value}")
        if workflow.error:
            lines.extend(["", f"Error: {workflow.error}"])
        metadata = {
            "_turn_complete": True,
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "workflow_status": workflow.status,
            "completion_notify_to": self._default_completion_notify_to,
        }
        content = "\n".join(lines)
        await self.bus.publish_outbound(
            OutboundMessage(
                channel=workflow.origin_channel,
                chat_id=workflow.origin_chat_id,
                content=content,
                metadata=metadata,
            )
        )
        await self._maybe_send_completion_email(workflow, content)

    async def _maybe_send_completion_email(self, workflow: WorkflowRecord, content: str) -> None:
        """Send workflow completion email directly from the workflow runner."""
        if not self.smtp_notifier:
            return
        recipient = self.smtp_notifier.resolve_recipient(self._default_completion_notify_to)
        if not recipient:
            return
        try:
            await self.smtp_notifier.send_workflow_completion(
                label=workflow.name,
                status=workflow.status,
                summary=content,
                workflow_id=workflow.id,
                to_addr=recipient,
            )
            logger.info(
                "Sent completion email for workflow {} to {}",
                workflow.id,
                recipient,
            )
        except Exception as exc:
            logger.error(
                "Failed to send completion email for workflow {} to {}: {}",
                workflow.id,
                recipient,
                exc,
            )
