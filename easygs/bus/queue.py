"""Async message queue for decoupled channel-agent communication."""

import asyncio
from typing import Callable, Awaitable

from loguru import logger

from easygs.bus.events import InboundMessage, OutboundMessage


class MessageBus:  # 异步消息总线
    """
    Async message bus that decouples chat channels from the agent core.
    
    Channels push messages to the inbound queue, and the agent processes
    them and pushes responses to the outbound queue.
    异步消息总线，用于将聊天频道与智能体核心解耦。频道将消息推送到入队队列，智能体处理这些消息并将响应推送到出队队列。
    """
    
    def __init__(self):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()  # 入站消息队列，存储接收到的消息，asyncio.Queue是线程安全的异步队列。前面是类型声明，队列里的元素是InboundMessage，后面则是创建队列实例
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()  # 出站消息队列，存储待发送的消息，asyncio.Queue是线程安全的异步队列
        self._outbound_subscribers: dict[str, list[Callable[[OutboundMessage], Awaitable[None]]]] = {}  # 出站消息订阅者：字典结构，key: 订阅标识（如通道名称），value: 回调函数列表，每个函数接收OutboundMessage 参数，返回Awaitable[None]（异步函数）订阅者模式：通道注册回调接收回复
        self._running = False  # 运行状态标志：标记该管理器是否处于运行状态
    
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Publish a message from a channel to the agent."""
        await self.inbound.put(msg)  # 频道调用：用户发来的消息放入队列，入队
    
    async def consume_inbound(self) -> InboundMessage:
        """Consume the next inbound message (blocks until available)."""
        return await self.inbound.get()  # Agent调用：取出下一条待处理的消息，出队
    
    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Publish a response from the agent to channels."""
        await self.outbound.put(msg)  # Agent调用：回复生成完毕，放入队列，入队
    
    async def consume_outbound(self) -> OutboundMessage:
        """Consume the next outbound message (blocks until available)."""
        return await self.outbound.get()  # 通道调用：取出下一条待发送的消息，出队
    
    def subscribe_outbound(
        self, 
        channel: str, 
        callback: Callable[[OutboundMessage], Awaitable[None]]
    ) -> None:
        """Subscribe to outbound messages for a specific channel."""
        if channel not in self._outbound_subscribers:
            self._outbound_subscribers[channel] = []
        self._outbound_subscribers[channel].append(callback)
    
    async def dispatch_outbound(self) -> None:
        """
        Dispatch outbound messages to subscribed channels.
        Run this as a background task.
        """
        self._running = True
        while self._running:
            try:
                msg = await asyncio.wait_for(self.outbound.get(), timeout=1.0)  # 取一条回复
                subscribers = self._outbound_subscribers.get(msg.channel, [])  # 
                for callback in subscribers:
                    try:
                        await callback(msg)  # 发送给对应的通道
                    except Exception as e:
                        logger.error(f"Error dispatching to {msg.channel}: {e}")
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the dispatcher loop."""
        self._running = False
    
    @property
    def inbound_size(self) -> int:
        """Number of pending inbound messages."""
        return self.inbound.qsize()
    
    @property
    def outbound_size(self) -> int:
        """Number of pending outbound messages."""
        return self.outbound.qsize()
