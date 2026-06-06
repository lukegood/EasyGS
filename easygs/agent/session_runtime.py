"""Per-session runtime that owns foreground turns."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from loguru import logger

from easygs.bus.events import InboundMessage, OutboundMessage


ProcessMessageFn = Callable[[InboundMessage, str | None], Awaitable[OutboundMessage | None]]
PublishOutboundFn = Callable[[OutboundMessage], Awaitable[None]]


class SessionRuntime:
    """Serialize foreground turns for one session.

    Background workflows run independently. Follow-up user messages stay in the
    foreground agent so it can answer questions immediately or explicitly add
    new instructions to a workflow through a tool.
    """

    def __init__(
        self,
        *,
        session_key: str,
        process_message: ProcessMessageFn,
        publish_outbound: PublishOutboundFn,
    ):
        self.session_key = session_key
        self._process_message = process_message
        self._publish_outbound = publish_outbound
        self._queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._state_lock = asyncio.Lock()

    async def enqueue(self, msg: InboundMessage) -> None:
        """Accept a message without blocking the global inbound dispatcher."""
        async with self._state_lock:
            was_running = bool(self._task and not self._task.done())
            await self._queue.put(msg)
            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._drain())
        if was_running:
            await self._publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=(
                        "已收到。当前大模型正在处理其他消息，此消息已排队。"
                        "稍后会继续处理此消息，无需重复发送。\n\n"
                        "Received. The model is currently processing another message, "
                        "so this message has been queued. It will be processed shortly, and no need to send it again."
                    ),
                    metadata={**(msg.metadata or {}), "_progress": True, "_turn_complete": True},
                )
            )

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _drain(self) -> None:
        while True:
            try:
                msg = await self._queue.get()
            except asyncio.CancelledError:
                break
            try:
                response = await self._process_message(msg, self.session_key)
                if response:
                    await self._publish_outbound(response)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error processing session {} message: {}", self.session_key, exc)
                await self._publish_outbound(
                    OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {exc}",
                        metadata={**(msg.metadata or {}), "_turn_complete": True},
                    )
                )
            finally:
                self._queue.task_done()
            async with self._state_lock:
                if self._queue.empty():
                    self._task = None
                    break
