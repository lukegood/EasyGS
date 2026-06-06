"""Data records for agentic EasyGS workflows."""

from dataclasses import dataclass, field
from typing import Any, Literal


WorkflowStatus = Literal["queued", "running", "waiting_user", "succeeded", "failed", "cancelled"]
WorkflowActionStatus = Literal["running", "succeeded", "failed", "cancelled"]


@dataclass
class WorkflowRecord:
    """Persistent record for one background agentic workflow."""

    id: str
    name: str
    status: WorkflowStatus = "queued"
    request: str = ""
    state: dict[str, Any] = field(default_factory=dict)
    origin_channel: str | None = None
    origin_chat_id: str | None = None
    notify_on_completion: bool = True
    work_dir: str = ""
    current_action_id: str | None = None
    iteration_count: int = 0
    final_summary: str = ""
    created_at_ms: int = 0
    updated_at_ms: int = 0
    started_at_ms: int | None = None
    completed_at_ms: int | None = None
    error: str | None = None


@dataclass
class WorkflowActionRecord:
    """Persistent record for one action executed by a workflow agent."""

    workflow_id: str
    action_id: str
    idx: int
    iteration: int
    tool_name: str
    tool_call_id: str = ""
    status: WorkflowActionStatus = "running"
    args: dict[str, Any] = field(default_factory=dict)
    result_preview: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    command: list[str] = field(default_factory=list)
    stdout_path: str = ""
    stderr_path: str = ""
    result_path: str = ""
    started_at_ms: int | None = None
    completed_at_ms: int | None = None
    exit_code: int | None = None
    error: str | None = None


@dataclass
class WorkflowArtifactRecord:
    """Workflow artifact discovered from action outputs."""

    workflow_id: str
    artifact_id: str
    producer_action_id: str
    name: str
    kind: str
    value: str
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
