"""Session management for conversation history."""

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from easygs.utils.helpers import ensure_dir, safe_filename


@dataclass
class Session:
    """
    A conversation session.
    
    Stores messages in JSONL format for easy reading and persistence.
    """
    
    key: str  # channel:chat_id  会话唯一标识
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the session."""
        msg = {
            "role": role,  # 角色: system/user/assistant/tool
            "content": content,  # 消息内容
            "timestamp": datetime.now().isoformat(),  # ISO时间戳
            **kwargs
        }
        self.messages.append(msg)  # 加入消息列表
        self.updated_at = datetime.now()  # 会话更新时间
    
    def get_history(self, max_messages: int = 50) -> list[dict[str, Any]]:
        """
        Get message history for LLM context.
        
        Args:
            max_messages: Maximum messages to return.
        
        Returns:
            List of messages in LLM format.
        """
        # Get recent messages  # 取最近的max——messages条消息
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        
        # Convert to LLM format (just role and content)  转换成大模型格式
        return [{"role": m["role"], "content": m["content"]} for m in recent]
    
    def clear(self) -> None:  # 清除session中的所有消息
        """Clear all messages in the session."""
        self.messages = []
        self.updated_at = datetime.now()  # 更新时间


class SessionManager:  # 管理会话
    """
    Manages conversation sessions.
    
    Sessions are stored as JSONL files in the sessions directory.  会话以JSONL文件存储在sessions目录中
    """
    
    def __init__(self, workspace: Path, research_mode: bool = True):
        self.workspace = workspace  # workspace地址
        self.sessions_dir = ensure_dir(Path.home() / ".easygs" / "sessions")
        self.research_mode = research_mode
        self._cache: dict[str, Session] = {}  # 内存缓存，key是session的key,避免频繁读写硬盘

    @staticmethod
    def _should_persist_in_research_mode(key: str) -> bool:
        """Persist browser chat sessions so WebUI history survives refreshes."""
        return key.startswith("websocket:")
    
    def _get_session_path(self, key: str) -> Path:  # 根据key生成session文件路径，将key中的：替换成_确保文件名合法
        """Get the file path for a session."""
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"
    
    def get_or_create(self, key: str) -> Session:
        """
        Get an existing session or create a new one.
        
        Args:
            key: Session key (usually channel:chat_id).
        
        Returns:
            The session.  获取或创建会话
        """
        # Check cache
        if key in self._cache:
            return self._cache[key]

        # Try to load from disk  缓存未命中，从硬盘加载
        session = None
        if (not self.research_mode) or self._should_persist_in_research_mode(key):  # 如果不是research模式，可以尝试从硬盘加载session
            session = self._load(key)
        if session is None:  # 文件不存在的时候创建新会话
            session = Session(key=key)
        
        self._cache[key] = session  # 存入缓存
        return session  # 返回会话
    
    def _load(self, key: str) -> Session | None:
        """Load a session from disk."""
        path = self._get_session_path(key)
        
        if not path.exists():
            return None
        
        try:  # 从硬盘上读取session
            messages = []
            metadata = {}
            created_at = None
            updated_at = None
            
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    data = json.loads(line)
                    
                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
                    else:
                        messages.append(data)
            
            return Session(  # 从硬盘上读取后，转为session对象
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                updated_at=updated_at or datetime.now(),
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to load session {key}: {e}")
            return None
    
    def save(self, session: Session) -> None:  # 保存会话到磁盘
        """Save a session to disk."""
        if self.research_mode and not self._should_persist_in_research_mode(session.key):
            logger.info("SessionManager.save skipped because research_mode is enabled: {}", session.key)
            return
        path = self._get_session_path(session.key)  # 获取路径
        
        with open(path, "w") as f:  # 以写模式打开
            # Write metadata first
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            }
            f.write(json.dumps(metadata_line) + "\n")
            
            # Write messages
            for msg in session.messages:
                f.write(json.dumps(msg) + "\n")
        
        self._cache[session.key] = session  # 更新内容缓存
    
    def delete(self, key: str) -> bool:  # 删除内存和硬盘上的session
        """
        Delete a session.
        
        Args:
            key: Session key.
        
        Returns:
            True if deleted, False if not found.
        """
        # Remove from cache 从缓存中移除
        self._cache.pop(key, None)
        
        # Remove file  从硬盘中移除
        path = self._get_session_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def delete_session(self, key: str) -> bool:
        """Compatibility wrapper used by the WebUI REST surface."""
        return self.delete(key)

    def read_session_file(self, key: str) -> dict[str, Any] | None:
        """Load a session from disk without caching for read-only WebUI endpoints."""
        path = self._get_session_path(key)
        if not path.exists():
            return None
        try:
            messages: list[dict[str, Any]] = []
            metadata: dict[str, Any] = {}
            created_at: str | None = None
            updated_at: str | None = None
            stored_key: str | None = None
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = data.get("created_at")
                        updated_at = data.get("updated_at")
                        stored_key = data.get("key")
                    else:
                        messages.append(data)
            return {
                "key": stored_key or key,
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": metadata,
                "messages": messages,
            }
        except Exception as e:
            logger.warning(f"Failed to read session {key}: {e}")
            return None
    
    def list_sessions(self) -> list[dict[str, Any]]:  # list所有的session
        """
        List all sessions.
        
        Returns:
            List of session info dicts.
        """
        sessions = []
        
        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                preview = ""
                with open(path) as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            key = data.get("key") or path.stem.replace("_", ":")
                            preview = self._read_preview(f)
                            sessions.append({
                                "key": key,
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "preview": preview,
                                "path": str(path)
                            })
            except Exception:
                continue
        
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)

    def _read_preview(self, lines: Any) -> str:
        """Return the first conversational user message for sidebar display."""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("role") != "user":
                continue
            content = data.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return ""
