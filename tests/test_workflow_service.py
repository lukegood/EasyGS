import asyncio
import os
from pathlib import Path
import sys

import pytest

from easygs.agent.loop import AgentLoop
from easygs.agent.tools.base import Tool
from easygs.agent.tools.registry import ToolRegistry
from easygs.agent.tools.workflow import WorkflowActionResult
from easygs.bus.queue import MessageBus
from easygs.providers.base import LLMResponse, ToolCallRequest
from easygs.workflows.schema import WorkflowRecord
from easygs.workflows.service import WorkflowService


class _FakeProvider:
    def __init__(self):
        self.calls = 0

    def get_default_model(self):
        return "fake-model"

    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.7):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content="I will create the first artifact.",
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="fake_write",
                        arguments={"prefix": "../unsafe_first"},
                    )
                ],
            )
        return LLMResponse(content="Workflow finished after inspecting the generated artifact.")


class _FakeActionTool(Tool):
    @property
    def name(self) -> str:
        return "fake_write"

    @property
    def description(self) -> str:
        return "Write a fake workflow artifact."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prefix": {"type": "string"},
            },
        }

    async def execute(self, **kwargs):
        return "Error: use inside workflow"

    async def execute_workflow_action(self, *, args, action_dir, stdout_path, stderr_path):
        prefix = Path(str(args.get("prefix") or "first")).name
        output_path = action_dir / f"{prefix}.txt"
        sidecar_path = action_dir / "extra_metrics.tsv"
        output_path.write_text("first", encoding="utf-8")
        sidecar_path.write_text("metric\tvalue\nn\t1\n", encoding="utf-8")
        stdout_path.write_text("wrote artifact\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return WorkflowActionResult(
            content=f"fake_write completed: {output_path}",
            outputs={"output_path": str(output_path)},
            command=["fake_write", prefix],
            exit_code=0,
        )


class _BlockingActionTool(Tool):
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    @property
    def name(self) -> str:
        return "blocking_action"

    @property
    def description(self) -> str:
        return "Block until the test releases the action."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        return "Error: use inside workflow"

    async def execute_workflow_action(self, *, args, action_dir, stdout_path, stderr_path):
        self.started.set()
        await self.release.wait()
        stdout_path.write_text("released\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return WorkflowActionResult(content="blocking_action completed", exit_code=0)


class _InboxProvider:
    def __init__(self):
        self.calls = 0
        self.snapshots: list[str] = []

    def get_default_model(self):
        return "fake-model"

    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.7):
        self.calls += 1
        self.snapshots.append("\n".join(str(msg.get("content", "")) for msg in messages))
        if self.calls == 1:
            return LLMResponse(
                content="I will run one blocking action.",
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="blocking_action",
                        arguments={},
                    )
                ],
            )
        return LLMResponse(content="Workflow finished after reading the user's follow-up.")


class _SleepProvider:
    def __init__(self):
        self.calls = 0

    def get_default_model(self):
        return "fake-model"

    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.7):
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content="I will run a long action.",
                tool_calls=[
                    ToolCallRequest(
                        id="call_1",
                        name="sleep_action",
                        arguments={},
                    )
                ],
            )
        return LLMResponse(content="Workflow finished unexpectedly.")


class _SleepActionTool(Tool):
    @property
    def name(self) -> str:
        return "sleep_action"

    @property
    def description(self) -> str:
        return "Run a long command through the workflow command runner."

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        return "Error: use inside workflow"

    async def execute_workflow_action(
        self,
        *,
        args,
        action_dir,
        stdout_path,
        stderr_path,
        command_runner,
    ):
        command = [sys.executable, "-c", "import time; time.sleep(30)"]
        exit_code = await command_runner(command, stdout_path, stderr_path, action_dir)
        return WorkflowActionResult(
            content=f"sleep_action exited with {exit_code}",
            command=command,
            exit_code=exit_code,
            error=None if exit_code == 0 else f"Process exited with code {exit_code}",
        )


class _FakeSmtpNotifier:
    default_recipient = "fallback@example.com"

    def __init__(self):
        self.calls = []

    def resolve_recipient(self, to_addr=None):
        return (to_addr or self.default_recipient or "").strip().lower()

    async def send_workflow_completion(self, **kwargs):
        self.calls.append(kwargs)


def _tool_registry_factory(_workflow):
    registry = ToolRegistry()
    registry.register(_FakeActionTool())
    return registry


def _blocking_tool_registry_factory(tool):
    def factory(_workflow):
        registry = ToolRegistry()
        registry.register(tool)
        return registry

    return factory


def _sleep_tool_registry_factory(_workflow):
    registry = ToolRegistry()
    registry.register(_SleepActionTool())
    return registry


def _count_open_fds_to(path: Path) -> int:
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.exists():
        pytest.skip("/proc/self/fd is not available on this platform")
    target = str(path)
    count = 0
    for fd in fd_dir.iterdir():
        try:
            if str(fd.resolve()) == target:
                count += 1
        except FileNotFoundError:
            continue
    return count


async def _wait_for_done(service: WorkflowService, workflow_id: str):
    for _ in range(100):
        workflow = service.get_workflow(workflow_id)
        if workflow and workflow.status in {"succeeded", "failed", "cancelled"}:
            return workflow
        await asyncio.sleep(0.05)
    raise AssertionError("workflow did not finish")


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


async def _wait_for_process_gone(pid: int):
    for _ in range(100):
        if not _pid_exists(pid):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"process {pid} is still alive")


@pytest.mark.asyncio
async def test_agentic_workflow_runs_action_and_records_artifact(tmp_path):
    bus = MessageBus()
    provider = _FakeProvider()
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=bus,
        workspace=tmp_path,
        provider=provider,
        tool_registry_factory=_tool_registry_factory,
        max_iterations=5,
    )
    try:
        workflow = await service.submit_workflow(
            request="Create a fake artifact and summarize it.",
            name="agentic_test",
            origin_channel="test",
            origin_chat_id="chat",
        )

        finished = await _wait_for_done(service, workflow.id)
        assert finished.status == "succeeded"
        assert "Workflow finished" in finished.final_summary

        actions = service.get_actions(workflow.id)
        assert len(actions) == 1
        assert actions[0].tool_name == "fake_write"
        assert actions[0].status == "succeeded"
        assert Path(actions[0].outputs["output_path"]).read_text(encoding="utf-8") == "first"
        assert Path(actions[0].outputs["output_path"]).name == "unsafe_first.txt"
        assert str(Path(actions[0].outputs["output_path"])).startswith(str(Path(finished.work_dir)))

        artifacts = service.get_artifacts(workflow.id)
        artifact_by_name = {artifact.name: artifact for artifact in artifacts}
        assert set(artifact_by_name) == {"output_path", "extra_metrics.tsv"}
        assert artifact_by_name["output_path"].value == actions[0].outputs["output_path"]
        assert artifact_by_name["output_path"].metadata["discovery"] == "metadata"
        assert artifact_by_name["extra_metrics.tsv"].kind == "discovered_file"
        assert artifact_by_name["extra_metrics.tsv"].metadata["discovery"] == "action_dir"
    finally:
        service.stop()


def test_workflow_status_queries_do_not_leak_sqlite_fds(tmp_path):
    db_path = tmp_path / "workflows.db"
    service = WorkflowService(
        store_path=db_path,
        bus=MessageBus(),
        workspace=tmp_path,
    )
    try:
        before = _count_open_fds_to(db_path)
        for _ in range(25):
            service.list_workflows()
        after = _count_open_fds_to(db_path)
        assert after == before
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_workflow_completion_metadata_includes_default_email_recipient(tmp_path):
    bus = MessageBus()
    provider = _FakeProvider()
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=bus,
        workspace=tmp_path,
        provider=provider,
        tool_registry_factory=_tool_registry_factory,
        default_completion_notify_to="notify@example.com",
    )
    try:
        workflow = await service.submit_workflow(
            request="Create an artifact.",
            name="email_notify_test",
            origin_channel="websocket",
            origin_chat_id="chat",
        )

        finished = await _wait_for_done(service, workflow.id)
        assert finished.status == "succeeded"

        message = await asyncio.wait_for(bus.consume_outbound(), timeout=1.0)
        assert message.channel == "websocket"
        assert message.chat_id == "chat"
        assert message.metadata["workflow_id"] == workflow.id
        assert message.metadata["workflow_name"] == "email_notify_test"
        assert message.metadata["workflow_status"] == "succeeded"
        assert message.metadata["completion_notify_to"] == "notify@example.com"
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_workflow_drains_user_messages_between_actions(tmp_path):
    bus = MessageBus()
    provider = _InboxProvider()
    action_tool = _BlockingActionTool()
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=bus,
        workspace=tmp_path,
        provider=provider,
        tool_registry_factory=_blocking_tool_registry_factory(action_tool),
        max_iterations=5,
    )
    try:
        workflow = await service.submit_workflow(
            request="Run an action, then continue.",
            name="inbox_test",
            origin_channel="websocket",
            origin_chat_id="chat",
        )
        await asyncio.wait_for(action_tool.started.wait(), timeout=1.0)
        assert service.add_user_message(workflow.id, "group.txt needs to be treated as updated context")
        action_tool.release.set()

        finished = await _wait_for_done(service, workflow.id)
        assert finished.status == "succeeded"
        assert any("group.txt needs to be treated" in snapshot for snapshot in provider.snapshots[1:])
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_cancel_queued_workflow_marks_cancelled(tmp_path):
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=MessageBus(),
        workspace=tmp_path,
        process_termination_grace_seconds=0.05,
    )
    try:
        workflow = WorkflowRecord(
            id=service.generate_workflow_id(),
            name="queued_cancel_test",
            status="queued",
            request="Queue but do not run.",
            state={"messages": []},
            origin_channel="test",
            origin_chat_id="chat",
            work_dir=str(tmp_path / "queued_cancel_test"),
            created_at_ms=1,
            updated_at_ms=1,
        )
        service._write_state(workflow)
        service._insert_workflow(workflow)

        result = await service.cancel_workflow(workflow.id, reason="test requested")
        assert "cancelled" in result

        cancelled = service.get_workflow(workflow.id)
        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert "test requested" in (cancelled.error or "")
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_cancel_running_workflow_kills_recorded_process_group(tmp_path):
    service = WorkflowService(
        store_path=tmp_path / "workflows.db",
        bus=MessageBus(),
        workspace=tmp_path,
        provider=_SleepProvider(),
        tool_registry_factory=_sleep_tool_registry_factory,
        max_iterations=3,
        process_termination_grace_seconds=0.05,
    )
    try:
        workflow = await service.submit_workflow(
            request="Run a long command.",
            name="running_cancel_test",
            origin_channel="test",
            origin_chat_id="chat",
        )

        pid = None
        for _ in range(100):
            rows = service._running_process_rows(workflow.id)
            if rows:
                pid = int(rows[0]["pid"])
                break
            await asyncio.sleep(0.05)
        assert pid is not None
        assert _pid_exists(pid)

        result = await service.cancel_workflow(workflow.id, reason="stop test")
        assert "cancelled" in result

        finished = await _wait_for_done(service, workflow.id)
        assert finished.status == "cancelled"
        assert "stop test" in (finished.error or "")

        actions = service.get_actions(workflow.id)
        assert actions
        assert actions[0].status == "cancelled"
        await _wait_for_process_gone(pid)
    finally:
        service.stop()


@pytest.mark.asyncio
async def test_completion_email_supports_workflow_metadata():
    notifier = _FakeSmtpNotifier()
    loop = object.__new__(AgentLoop)
    loop.smtp_notifier = notifier

    await AgentLoop._maybe_send_completion_email(
        loop,
        {
            "workflow_id": "wf_123",
            "workflow_name": "qc_workflow",
            "workflow_status": "succeeded",
        },
        "Workflow finished cleanly.",
    )

    assert notifier.calls == [
        {
            "label": "qc_workflow",
            "status": "succeeded",
            "summary": "Workflow finished cleanly.",
            "workflow_id": "wf_123",
            "to_addr": "fallback@example.com",
        }
    ]
