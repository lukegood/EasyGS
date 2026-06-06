from pathlib import Path
import json

import pytest

from easygs.bus.events import OutboundMessage
from easygs.bus.queue import MessageBus
from easygs.channels.manager import ChannelManager
from easygs.channels.websocket import WebSocketChannel
from easygs.config.schema import Config
from easygs.session.manager import SessionManager


class FakeConnection:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, raw: str) -> None:
        self.sent.append(raw)


def test_websocket_channel_registered_when_enabled(tmp_path: Path) -> None:
    config = Config()
    config.channels.websocket.enabled = True
    sessions = SessionManager(tmp_path / "workspace", research_mode=True)

    manager = ChannelManager(config, MessageBus(), session_manager=sessions)

    assert "websocket" in manager.channels
    assert manager.channels["websocket"].config.port == 25685


def test_research_mode_persists_websocket_sessions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = SessionManager(tmp_path / "workspace", research_mode=True)

    web_session = manager.get_or_create("websocket:chat-1")
    web_session.add_message("user", "hello")
    manager.save(web_session)

    payload = manager.read_session_file("websocket:chat-1")
    assert payload is not None
    assert payload["key"] == "websocket:chat-1"
    assert payload["messages"][0]["content"] == "hello"
    assert manager.list_sessions()[0]["preview"] == "hello"

    cli_session = manager.get_or_create("cli:direct")
    cli_session.add_message("user", "do not persist")
    manager.save(cli_session)

    assert manager.read_session_file("cli:direct") is None


def test_session_list_preview_uses_first_user_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    manager = SessionManager(tmp_path / "workspace", research_mode=True)

    session = manager.get_or_create("websocket:chat-2")
    session.add_message("assistant", "assistant greeting")
    session.add_message("user", "first real question")
    session.add_message("user", "later follow-up")
    manager.save(session)

    sessions = manager.list_sessions()
    assert sessions[0]["preview"] == "first real question"


@pytest.mark.asyncio
async def test_websocket_channel_emits_stream_end_for_completed_turn() -> None:
    channel = WebSocketChannel(Config().channels.websocket, MessageBus())
    connection = FakeConnection()
    channel._subs["chat-1"] = {connection}

    await channel.send(OutboundMessage(
        channel="websocket",
        chat_id="chat-1",
        content="final answer",
        metadata={"_turn_complete": True},
    ))

    frames = [json.loads(raw) for raw in connection.sent]
    assert frames == [
        {
            "event": "message",
            "chat_id": "chat-1",
            "text": "final answer",
            "turn_complete": True,
        },
        {
            "event": "stream_end",
            "chat_id": "chat-1",
        },
    ]


@pytest.mark.asyncio
async def test_websocket_channel_emits_source_for_workflow_completion() -> None:
    channel = WebSocketChannel(Config().channels.websocket, MessageBus())
    connection = FakeConnection()
    channel._subs["chat-1"] = {connection}

    await channel.send(OutboundMessage(
        channel="websocket",
        chat_id="chat-1",
        content="workflow finished",
        metadata={
            "workflow_id": "wf_12345678",
            "workflow_name": "vcf_qc_pca",
            "workflow_status": "succeeded",
            "completion_notify_to": "private@example.com",
        },
    ))

    frame = json.loads(connection.sent[0])
    assert frame["source"] == {
        "kind": "workflow",
        "id": "wf_12345678",
        "name": "vcf_qc_pca",
        "status": "succeeded",
    }
    assert "completion_notify_to" not in frame["source"]
