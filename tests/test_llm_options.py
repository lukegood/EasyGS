from types import SimpleNamespace

import pytest

from easygs.agent.loop import AgentLoop
from easygs.bus.queue import MessageBus
from easygs.providers.base import LLMResponse
from easygs.providers.litellm_provider import LiteLLMProvider


class _RecordingProvider:
    def __init__(self):
        self.calls = []

    def get_default_model(self):
        return "fake-model"

    async def chat(
        self,
        messages,
        tools=None,
        model=None,
        max_tokens=4096,
        temperature=0.7,
        reasoning_effort=None,
    ):
        self.calls.append(
            {
                "messages": messages,
                "tools": tools,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "reasoning_effort": reasoning_effort,
            }
        )
        return LLMResponse(content="done")


@pytest.mark.asyncio
async def test_agent_loop_forwards_llm_options(tmp_path, monkeypatch):
    monkeypatch.setattr("easygs.agent.loop.get_data_dir", lambda: tmp_path)
    provider = _RecordingProvider()
    agent = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=tmp_path,
        model="deepseek-v4-pro",
        max_tokens=384000,
        reasoning_effort="max",
    )

    result = await agent.process_direct("hello")

    assert result == "done"
    assert provider.calls
    assert provider.calls[0]["model"] == "deepseek-v4-pro"
    assert provider.calls[0]["max_tokens"] == 384000
    assert provider.calls[0]["reasoning_effort"] == "max"


@pytest.mark.asyncio
async def test_litellm_provider_forwards_reasoning_effort(monkeypatch):
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        message = SimpleNamespace(content="ok", tool_calls=None, reasoning_content="thinking")
        choice = SimpleNamespace(message=message, finish_reason="stop")
        usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        return SimpleNamespace(choices=[choice], usage=usage)

    monkeypatch.setattr("easygs.providers.litellm_provider.acompletion", fake_acompletion)

    provider = LiteLLMProvider(api_key="sk-test", default_model="deepseek-v4-pro")
    response = await provider.chat(
        messages=[{"role": "user", "content": "hello"}],
        model="deepseek-v4-pro",
        max_tokens=384000,
        reasoning_effort="max",
    )

    assert captured["model"] == "deepseek/deepseek-v4-pro"
    assert captured["max_tokens"] == 384000
    assert captured["reasoning_effort"] == "max"
    assert response.content == "ok"
    assert response.reasoning_content == "thinking"
