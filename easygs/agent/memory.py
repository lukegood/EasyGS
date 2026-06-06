"""Memory system for persistent agent memory."""

from pathlib import Path

from easygs.utils.helpers import ensure_dir


class MemoryStore:
    """Two-layer memory: MEMORY.md (long-term facts) + HISTORY.md (grep-searchable log)."""

    def __init__(self, workspace: Path, research_mode: bool = True):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
        self.research_mode = research_mode

    def read_long_term(self) -> str:  # 读取记忆文件
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:  # 写记忆文件
        if self.research_mode:  # research模式下不需要写长期记忆
            return
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:  # 写历史文件
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:  # 读取memory的内容
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""
