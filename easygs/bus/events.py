"""Event types for the message bus."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass  # 数据类装饰器，自动为数据类生成常用方法，包括构造函数等等。构造函数只需要声明成员，不需要写构造函数了
class InboundMessage:  # 入队消息数据类
    """Message received from a chat channel."""
    
    channel: str  # telegram, discord, slack, whatsapp  通道类型
    sender_id: str  # User identifier  发送者ID
    chat_id: str  # Chat/channel identifier  聊天/频道ID
    content: str  # Message text  消息内容
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳
    media: list[str] = field(default_factory=list)  # Media URLs  媒体文件URL列表
    metadata: dict[str, Any] = field(default_factory=dict)  # Channel-specific data  频道特定的额外数据
    
    @property
    def session_key(self) -> str:  # 返回唯一会话标识
        """Unique key for session identification."""
        return f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:  # 出队数据类
    """Message to send to a chat channel."""
    
    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


