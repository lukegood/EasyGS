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
    task_started_at_ms: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    llm_call_count: int = 0
    usage_reported_call_count: int = 0
    error: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def usage_complete(self) -> bool:
        return (
            self.llm_call_count > 0
            and self.llm_call_count == self.usage_reported_call_count
        )

    def runtime_ms(self, now_ms: int | None = None) -> int | None:
        """Return task runtime with background queue waiting removed.

        The existing task boundary is preserved: runtime starts when the foreground
        request starts and ends when the workflow completes (or at ``now_ms``).  The
        interval after workflow creation but before a worker starts it is excluded.
        """
        if self.task_started_at_ms is None:
            return None
        end_ms = self.completed_at_ms if self.completed_at_ms is not None else now_ms
        if end_ms is None:
            return None
        elapsed_ms = max(0, end_ms - self.task_started_at_ms)
        if self.created_at_ms <= 0:
            return elapsed_ms

        queue_end_ms = self.started_at_ms if self.started_at_ms is not None else end_ms
        queue_overlap_start_ms = max(self.task_started_at_ms, self.created_at_ms)
        queue_overlap_end_ms = min(end_ms, queue_end_ms)
        queued_ms = max(0, queue_overlap_end_ms - queue_overlap_start_ms)
        return max(0, elapsed_ms - queued_ms)


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
