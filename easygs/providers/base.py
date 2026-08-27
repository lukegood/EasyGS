"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping


def _usage_int(usage: Mapping[str, Any], *keys: str) -> int | None:
    """Return the first non-negative integer usage value for the requested keys."""
    for key in keys:
        value = usage.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if number >= 0:
            return number
    return None


def normalize_token_usage(usage: Mapping[str, Any] | None) -> tuple[int, int] | None:
    """Normalize provider usage into total input and output tokens.

    ``total_tokens - output_tokens`` is preferred because OpenAI-compatible
    gateways (including ccLoad) report cached input inside ``total_tokens``.
    When an Anthropic-style response separates uncached input from cache read
    and cache creation tokens, those cache fields are added exactly once.
    """
    if not usage:
        return None

    output_tokens = _usage_int(usage, "completion_tokens", "output_tokens")
    total_tokens = _usage_int(usage, "total_tokens")
    if total_tokens is not None and output_tokens is not None and total_tokens >= output_tokens:
        return total_tokens - output_tokens, output_tokens

    prompt_tokens = _usage_int(usage, "prompt_tokens")
    input_tokens = prompt_tokens
    if input_tokens is None:
        input_tokens = _usage_int(usage, "input_tokens")
        if input_tokens is not None:
            input_tokens += _usage_int(
                usage, "cache_read_input_tokens", "cache_read_tokens"
            ) or 0
            input_tokens += _usage_int(
                usage, "cache_creation_input_tokens", "cache_creation_tokens"
            ) or 0

    if output_tokens is None and total_tokens is not None and input_tokens is not None:
        if total_tokens >= input_tokens:
            output_tokens = total_tokens - input_tokens

    if input_tokens is None or output_tokens is None:
        return None
    return input_tokens, output_tokens


@dataclass
class TokenUsageAccumulator:
    """Accumulate normalized usage while retaining completeness diagnostics."""

    input_tokens: int = 0
    output_tokens: int = 0
    llm_call_count: int = 0
    usage_reported_call_count: int = 0

    def add(self, usage: Mapping[str, Any] | None) -> None:
        self.llm_call_count += 1
        normalized = normalize_token_usage(usage)
        if normalized is None:
            return
        input_tokens, output_tokens = normalized
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.usage_reported_call_count += 1

    @property
    def usage_complete(self) -> bool:
        return (
            self.llm_call_count > 0
            and self.llm_call_count == self.usage_reported_call_count
        )


@dataclass
class ToolCallRequest:
    """A tool call request from the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    reasoning_content: str | None = None  # Kimi, DeepSeek-R1 etc.
    
    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Implementations should handle the specifics of each provider's API
    while maintaining a consistent interface.
    """
    
    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        self.api_base = api_base
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions.
            model: Model identifier (provider-specific).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
            reasoning_effort: Optional model reasoning intensity.
        
        Returns:
            LLMResponse with content and/or tool calls.
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        pass
