"""Tools for agentic workflow submission and inspection."""

from typing import Any, TYPE_CHECKING

from easygs.agent.tools.base import Tool

if TYPE_CHECKING:
    from easygs.workflows.service import WorkflowService


class SubmitWorkflowTool(Tool):
    """Submit a background agentic workflow."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
        self._last_execution_metadata: dict[str, Any] = {}

    @property
    def terminal_after_execution(self) -> bool:
        return True

    @property
    def last_execution_metadata(self) -> dict[str, Any]:
        return dict(self._last_execution_metadata)

    def set_context(self, channel: str, chat_id: str) -> None:
        self._origin_channel = channel
        self._origin_chat_id = chat_id

    @property
    def name(self) -> str:
        return "submit_workflow"

    @property
    def description(self) -> str:
        return (
            "Submit an agentic EasyGS workflow. Use this as the execution handoff when "
            "the user asks EasyGS to perform a bioinformatics, genomics, genetic, or "
            "statistical genetics analysis. The foreground agent may inspect inputs first, "
            "then submit the workflow with enough context for the workflow agent to execute "
            "the analysis, inspect outputs, adapt to dependent results, and summarize completion."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "request": {
                    "type": "string",
                    "description": (
                        "The full workflow request, including the original user goal, discovered "
                        "input files, relevant foreground observations, assumptions, planned "
                        "steps, and expected outputs when known."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Optional short workflow name.",
                },
                "notify_on_completion": {
                    "type": "boolean",
                    "description": "Whether to notify the origin chat when the workflow completes. Defaults to true.",
                },
                "output_dir": {
                    "type": "string",
                    "description": (
                        "Optional user-requested directory where the workflow should run and "
                        "write all state, logs, and analysis outputs."
                    ),
                },
                "plan_summary": {
                    "type": "string",
                    "description": "Optional concise summary of how the workflow agent should approach the task.",
                },
                "planned_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional planned steps to show the user before the background workflow continues.",
                },
                "expected_outputs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional expected outputs or artifacts.",
                },
            },
            "required": ["request"],
        }

    async def execute(
        self,
        request: str,
        name: str | None = None,
        notify_on_completion: bool = True,
        output_dir: str | None = None,
        plan_summary: str | None = None,
        planned_steps: list[str] | None = None,
        expected_outputs: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        workflow = await self._workflows.submit_workflow(
            request=request,
            name=name,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
            notify_on_completion=notify_on_completion,
            output_dir=output_dir,
            plan_summary=plan_summary,
            planned_steps=planned_steps,
            expected_outputs=expected_outputs,
        )
        self._last_execution_metadata = {
            "active_workflow_id": workflow.id,
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
        }
        lines = [
            f"Background workflow submitted: `{workflow.id}`",
            f"Name: {workflow.name}",
            "Status: queued",
            f"Work dir: {workflow.work_dir}",
        ]
        if plan_summary:
            lines.extend(["", "Plan:", str(plan_summary).strip()])
        if planned_steps:
            lines.append("")
            lines.append("Planned steps:")
            lines.extend(f"- {step}" for step in planned_steps if str(step).strip())
        if expected_outputs:
            lines.append("")
            lines.append("Expected outputs:")
            lines.extend(f"- {item}" for item in expected_outputs if str(item).strip())
        lines.extend(
            [
                "",
                "I will continue the analysis in this background workflow. You can ask for status "
                "while it runs; if you provide a correction or new constraint, I can add that "
                "message to the workflow context.",
            ]
        )
        return (
            "\n".join(lines)
        )


class GetWorkflowStatusTool(Tool):
    """Inspect workflow status."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows

    @property
    def name(self) -> str:
        return "get_workflow_status"

    @property
    def description(self) -> str:
        return "Get the current status of a background workflow by workflow ID."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "The workflow ID."},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, workflow_id: str, **kwargs: Any) -> str:
        return self._workflows.format_status(workflow_id)


class GetActiveWorkflowStatusTool(Tool):
    """Inspect the active workflow for the current chat."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        self._origin_channel = channel
        self._origin_chat_id = chat_id

    @property
    def name(self) -> str:
        return "get_active_workflow_status"

    @property
    def description(self) -> str:
        return (
            "Get the newest active background workflow status for the current chat, "
            "without requiring the user to provide a workflow ID."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs: Any) -> str:
        workflow = self._workflows.find_active_for_origin(self._origin_channel, self._origin_chat_id)
        if not workflow:
            return "No active background workflow is running for this chat."
        return self._workflows.format_status(workflow.id)


class AddWorkflowMessageTool(Tool):
    """Append new user context to a running workflow."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        self._origin_channel = channel
        self._origin_chat_id = chat_id

    @property
    def name(self) -> str:
        return "add_workflow_message"

    @property
    def description(self) -> str:
        return (
            "Add a correction, new constraint, or extra instruction to a running workflow's "
            "context. Use this only when the user wants the workflow to incorporate new "
            "information. Do not use it for status checks or ordinary conversation."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The new instruction or context to add to the workflow.",
                },
                "workflow_id": {
                    "type": "string",
                    "description": "Optional workflow ID. If omitted, the newest active workflow for this chat is used.",
                },
            },
            "required": ["message"],
        }

    async def execute(self, message: str, workflow_id: str | None = None, **kwargs: Any) -> str:
        target_id = workflow_id
        if not target_id:
            workflow = self._workflows.find_active_for_origin(self._origin_channel, self._origin_chat_id)
            if not workflow:
                return "No active background workflow is running for this chat."
            target_id = workflow.id

        if not self._workflows.add_user_message(target_id, message):
            return f"Error: workflow `{target_id}` is not active or was not found."
        workflow = self._workflows.get_workflow(target_id)
        status = workflow.status if workflow else "unknown"
        current = workflow.current_action_id if workflow else None
        lines = [
            f"Added this message to workflow `{target_id}`.",
            f"- Status: {status}",
            f"- Current action: {current or 'n/a'}",
            "The workflow will incorporate it at the next checkpoint.",
        ]
        return "\n".join(lines)


class CancelWorkflowTool(Tool):
    """Cancel an active workflow."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        self._origin_channel = channel
        self._origin_chat_id = chat_id

    @property
    def name(self) -> str:
        return "cancel_workflow"

    @property
    def description(self) -> str:
        return (
            "Cancel a queued or running background workflow. Use this when the user explicitly "
            "asks to stop, cancel, abort, or terminate a workflow."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "Optional workflow ID. If omitted, the newest active workflow for this chat is used.",
                },
                "reason": {
                    "type": "string",
                    "description": "Optional user-facing reason for cancellation.",
                },
            },
        }

    async def execute(
        self,
        workflow_id: str | None = None,
        reason: str | None = None,
        **kwargs: Any,
    ) -> str:
        target_id = workflow_id
        if not target_id:
            workflow = self._workflows.find_active_for_origin(self._origin_channel, self._origin_chat_id)
            if not workflow:
                return "No active background workflow is running for this chat."
            target_id = workflow.id
        return await self._workflows.cancel_workflow(target_id, reason=reason)


class GetWorkflowResultTool(Tool):
    """Return the final result for a workflow."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows

    @property
    def name(self) -> str:
        return "get_workflow_result"

    @property
    def description(self) -> str:
        return "Get the final result summary for a completed background workflow."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "The workflow ID."},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, workflow_id: str, **kwargs: Any) -> str:
        return self._workflows.format_result(workflow_id)


class ListWorkflowStatusesTool(Tool):
    """List workflows and their statuses."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows

    @property
    def name(self) -> str:
        return "list_workflow_statuses"

    @property
    def description(self) -> str:
        return "List background workflows with status summaries."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Optional status filter: all, queued, running, waiting_user, succeeded, failed, cancelled.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of workflows to return. Defaults to 20.",
                },
            },
        }

    async def execute(
        self,
        status: str = "all",
        limit: int = 20,
        **kwargs: Any,
    ) -> str:
        return self._workflows.format_listing(status=status, limit=limit)


class ListWorkflowCapabilitiesTool(Tool):
    """List tools available to the workflow-internal agent."""

    def __init__(self, workflows: "WorkflowService"):
        self._workflows = workflows

    @property
    def name(self) -> str:
        return "list_workflow_capabilities"

    @property
    def description(self) -> str:
        return "List action tools available inside background agentic workflows."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._workflows.format_capabilities()
