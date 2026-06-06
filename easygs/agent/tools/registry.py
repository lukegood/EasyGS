"""Tool registry for dynamic tool management."""

from dataclasses import dataclass, field
from typing import Any

from easygs.agent.tools.base import Tool


@dataclass
class ToolExecutionResult:
    """Structured result returned by a tool execution."""

    content: str
    terminal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:  # 工具注册
    """
    Registry for agent tools.
    
    Allows dynamic registration and execution of tools.
    """
    
    def __init__(self):  # 空字典，等待工具注册
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:  # 注册工具
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:  # 注销工具
        """Unregister a tool by name."""
        self._tools.pop(name, None)
    
    def get(self, name: str) -> Tool | None:  # 获取工具
        """Get a tool by name."""
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:  # 检查是否有这个工具
        """Check if a tool is registered."""
        return name in self._tools
    
    def get_definitions(self) -> list[dict[str, Any]]:  # 获取所有工具的定义，转化为OpenAI格式
        """Get all tool definitions in OpenAI format."""
        return [tool.to_schema() for tool in self._tools.values()]

    def iter_tools(self) -> list[Tool]:
        """Return the registered tool instances."""
        return list(self._tools.values())
    
    async def execute_detailed(self, name: str, params: dict[str, Any]) -> ToolExecutionResult:
        """
        Execute a tool by name with given parameters and return structured control flags.
        
        Args:
            name: Tool name.
            params: Tool parameters. 是参数字典
        
        Returns:
            Tool execution result with optional control metadata.
        """
        tool = self._tools.get(name)  # 检查是否是工具，就是检查字典里键是否存在
        if not tool:  # 键不存在，报错
            return ToolExecutionResult(content=f"Error: Tool '{name}' not found")

        try:
            errors = tool.validate_params(params)  # 校验参数
            if errors:
                return ToolExecutionResult(
                    content=f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors)
                )
            content = await tool.execute(**params)  # 调用具体的工具执行
            metadata = getattr(tool, "last_execution_metadata", {})
            return ToolExecutionResult(
                content=content,
                terminal=bool(getattr(tool, "terminal_after_execution", False)),
                metadata=metadata if isinstance(metadata, dict) else {},
            )
        except Exception as e:
            return ToolExecutionResult(content=f"Error executing {name}: {str(e)}")

    async def execute(self, name: str, params: dict[str, Any]) -> str:  # 执行工具
        """
        Execute a tool by name with given parameters.

        This compatibility wrapper preserves the historic string-only API.
        """
        result = await self.execute_detailed(name, params)
        return result.content
    
    @property
    def tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools
