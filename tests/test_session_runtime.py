import asyncio
from dataclasses import dataclass

import pytest

from easygs.agent.session_runtime import SessionRuntime
from easygs.bus.events import InboundMessage, OutboundMessage


@dataclass
class _Workflow:
    id: str
    status: str = "running"
    current_action_id: str | None = "act_001_fake"


class _FakeWorkflows:
    def __init__(self):
        self.workflow = _Workflow(id="wf_active")
        self.messages: list[tuple[str, str]] = []

    def get_workflow(self, workflow_id):
        return self.workflow if workflow_id == self.workflow.id else None

    def find_active_for_origin(self, origin_channel, origin_chat_id):
        if self.workflow.status in {"queued", "running", "waiting_user"}:
            return self.workflow
        return None

    def add_user_message(self, workflow_id, content):
        self.messages.append((workflow_id, content))
        return True


@pytest.mark.asyncio
async def test_active_workflow_messages_stay_in_foreground_turn():
    outbox: list[OutboundMessage] = []
    processed: list[str] = []

    async def process_message(msg, session_key):
        processed.append(msg.content)
        return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content="foreground answer")

    async def publish(msg):
        outbox.append(msg)

    runtime = SessionRuntime(
        session_key="websocket:chat",
        process_message=process_message,
        publish_outbound=publish,
    )

    await runtime.enqueue(
        InboundMessage(
            channel="websocket",
            sender_id="user",
            chat_id="chat",
            content="现在到哪了？",
        )
    )

    for _ in range(50):
        if outbox:
            break
        await asyncio.sleep(0.02)

    assert processed == ["现在到哪了？"]
    assert outbox
    assert outbox[0].content == "foreground answer"


@pytest.mark.asyncio
async def test_busy_foreground_turn_acknowledges_queued_message():
    started = asyncio.Event()
    release = asyncio.Event()
    processed: list[str] = []
    outbox: list[OutboundMessage] = []

    async def process_message(msg, session_key):
        processed.append(msg.content)
        started.set()
        if msg.content == "first":
            await release.wait()
        return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"done {msg.content}")

    async def publish(msg):
        outbox.append(msg)

    runtime = SessionRuntime(
        session_key="websocket:chat",
        process_message=process_message,
        publish_outbound=publish,
    )

    await runtime.enqueue(InboundMessage(channel="websocket", sender_id="user", chat_id="chat", content="first"))
    await asyncio.wait_for(started.wait(), timeout=1.0)
    await runtime.enqueue(InboundMessage(channel="websocket", sender_id="user", chat_id="chat", content="second"))

    assert any("已排队" in msg.content for msg in outbox)

    release.set()
    for _ in range(50):
        if processed == ["first", "second"]:
            break
        await asyncio.sleep(0.02)
    assert processed == ["first", "second"]


@pytest.mark.asyncio
async def test_queued_message_stays_in_foreground_after_submit_binding():
    started = asyncio.Event()
    release = asyncio.Event()
    second_processed = asyncio.Event()
    processed: list[str] = []
    outbox: list[OutboundMessage] = []
    workflows = _FakeWorkflows()

    async def process_message(msg, session_key):
        processed.append(msg.content)
        started.set()
        if msg.content == "first":
            await release.wait()
        else:
            second_processed.set()
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content="submitted",
            metadata={"active_workflow_id": workflows.workflow.id},
        )

    async def publish(msg):
        outbox.append(msg)

    runtime = SessionRuntime(
        session_key="websocket:chat",
        process_message=process_message,
        publish_outbound=publish,
    )

    workflows.workflow.status = "succeeded"
    await runtime.enqueue(InboundMessage(channel="websocket", sender_id="user", chat_id="chat", content="first"))
    await asyncio.wait_for(started.wait(), timeout=1.0)
    await runtime.enqueue(InboundMessage(channel="websocket", sender_id="user", chat_id="chat", content="second"))

    workflows.workflow.status = "running"
    release.set()
    await asyncio.wait_for(second_processed.wait(), timeout=1.0)

    assert processed == ["first", "second"]
    assert workflows.messages == []
