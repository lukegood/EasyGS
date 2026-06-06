"""Agent loop: the core processing engine."""

import asyncio
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

from loguru import logger

from easygs.bus.events import InboundMessage, OutboundMessage
from easygs.bus.queue import MessageBus
from easygs.providers.base import LLMProvider
from easygs.agent.context import ContextBuilder
from easygs.agent.tools.workflows import (
    AddWorkflowMessageTool,
    CancelWorkflowTool,
    GetActiveWorkflowStatusTool,
    GetWorkflowResultTool,
    GetWorkflowStatusTool,
    ListWorkflowCapabilitiesTool,
    ListWorkflowStatusesTool,
    SubmitWorkflowTool,
)
from easygs.agent.tools.registry import ToolRegistry
from easygs.agent.tools.filesystem import (
    EditFileTool,
    ListDirTool,
    PreviewTabularFileTool,
    PreviewVcfFileTool,
    ReadFileTool,
    WriteFileTool,
)
from easygs.agent.tools.shell import ExecTool
from easygs.agent.tools.web import WebSearchTool, WebFetchTool
from easygs.agent.tools.message import MessageTool
from easygs.agent.tools.spawn import SpawnTool
from easygs.agent.tools.cron import CronTool
from easygs.agent.tools.workflow import AnalysisActionTool
from easygs.agent.workflows import build_analysis_workflows
from easygs.agent.memory import MemoryStore
from easygs.agent.subagent import SubagentManager
from easygs.agent.session_runtime import SessionRuntime
from easygs.config.loader import get_data_dir
from easygs.session.manager import SessionManager
from easygs.workflows.service import WorkflowService

if TYPE_CHECKING:
    from easygs.notifications.smtp import SmtpNotifier


class AgentLoop:
    """
    The agent loop is the core processing engine.
    
    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """
    
    def __init__(
        self,
        bus: MessageBus,  # wlg：消息总线，用于收发消息
        provider: LLMProvider,  
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,  # wlg：防止无限循环
        temperature: float = 0.7,  # wlg：LLM的温度参数
        memory_window: int = 50,  # wlg：内存窗口大小（会话保留的消息数）
        brave_api_key: str | None = None,  # Brave搜索API密钥
        exec_config: "ExecToolConfig | None" = None,  # Shell执行配置
        cron_service: "CronService | None" = None,  # 定时任务服务
        restrict_to_workspace: bool = False,  # 是否限制在工作区内操作
        session_manager: SessionManager | None = None,  # 会话管理器
        research_mode: bool = True,
        smtp_notifier: "SmtpNotifier | None" = None,
    ):
        from easygs.config.schema import ExecToolConfig
        from easygs.cron.service import CronService
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations  # 最大工具调用轮次（默认40）
        self.temperature = temperature
        self.memory_window = memory_window
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        self.research_mode = research_mode
        self.smtp_notifier = smtp_notifier
        
        self.context = ContextBuilder(workspace)  # 创建上下文
        self.sessions = session_manager or SessionManager(workspace, research_mode=research_mode)  # 管理会话
        self.tools = ToolRegistry()  # 工具注册
        self.analysis_workflows = build_analysis_workflows(
            workspace=self.workspace,
            restrict_to_workspace=self.restrict_to_workspace,
        )
        self.workflows = WorkflowService(
            store_path=get_data_dir() / "workflows" / "workflows.db",
            bus=bus,
            workspace=self.workspace,
            provider=self.provider,
            tool_registry_factory=self._build_workflow_tool_registry,
            model=self.model,
            temperature=0.2,
            max_iterations=self.max_iterations,
            default_completion_notify_to=(
                self.smtp_notifier.default_recipient if self.smtp_notifier else None
            ),
            smtp_notifier=self.smtp_notifier,
        )
        self.subagents = SubagentManager(  # 子Agent管理
            provider=provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            brave_api_key=brave_api_key,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
            research_mode=research_mode,
        )
        
        self._running = False
        self._session_runtimes: dict[str, SessionRuntime] = {}
        self._register_default_tools()  # 注册8种内置工具

    @staticmethod
    def _webui_completion_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        """Return only safe workflow fields needed for WebUI badges."""
        safe_keys = {
            "workflow_id",
            "workflow_name",
            "workflow_status",
        }
        return {
            key: value
            for key in safe_keys
            if (value := metadata.get(key)) not in (None, "")
        }
    
    def _register_default_tools(self) -> None:  # 注册工具，每个工具继承自Tool
        """Register the default set of tools."""
        # File tools (restrict to workspace if configured)  文件操作
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        self.tools.register(ReadFileTool(allowed_dir=allowed_dir))
        self.tools.register(PreviewTabularFileTool(allowed_dir=allowed_dir))
        self.tools.register(PreviewVcfFileTool(allowed_dir=allowed_dir))
        self.tools.register(WriteFileTool(allowed_dir=allowed_dir))
        self.tools.register(EditFileTool(allowed_dir=allowed_dir))
        self.tools.register(ListDirTool(allowed_dir=allowed_dir))
        
        # Shell tool  shell工具
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        
        # Web tools
        self.tools.register(WebSearchTool(api_key=self.brave_api_key))
        self.tools.register(WebFetchTool())

        # Background workflow tools
        self.tools.register(SubmitWorkflowTool(self.workflows))  # 注册workflow提交工具
        self.tools.register(GetActiveWorkflowStatusTool(self.workflows))  # 查询当前会话活跃workflow
        self.tools.register(AddWorkflowMessageTool(self.workflows))  # 显式追加消息到workflow上下文
        self.tools.register(CancelWorkflowTool(self.workflows))  # 取消正在运行的workflow
        self.tools.register(GetWorkflowStatusTool(self.workflows))  # 注册workflow状态查询工具
        self.tools.register(GetWorkflowResultTool(self.workflows))  # 注册workflow结果查询工具
        self.tools.register(ListWorkflowStatusesTool(self.workflows))  # 注册workflow列表工具
        self.tools.register(ListWorkflowCapabilitiesTool(self.workflows))  # 注册workflow能力查询工具

        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self.tools.register(message_tool)
        
        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self.subagents)
        self.tools.register(spawn_tool)
        
        # Cron tool (for scheduling)
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

    def _build_workflow_tool_registry(self, workflow: Any) -> ToolRegistry:
        """Build the isolated tool view used inside a background workflow."""
        tools = ToolRegistry()
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        tools.register(ReadFileTool(allowed_dir=allowed_dir))
        tools.register(PreviewTabularFileTool(allowed_dir=allowed_dir))
        tools.register(PreviewVcfFileTool(allowed_dir=allowed_dir))
        tools.register(WriteFileTool(allowed_dir=allowed_dir))
        tools.register(EditFileTool(allowed_dir=allowed_dir))
        tools.register(ListDirTool(allowed_dir=allowed_dir))
        tools.register(ExecTool(
            working_dir=str(Path(workflow.work_dir) if workflow.work_dir else self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
        ))
        tools.register(WebSearchTool(api_key=self.brave_api_key))
        tools.register(WebFetchTool())
        for workflow_def in self.analysis_workflows:
            tools.register(AnalysisActionTool(workflow_def.definition))
        return tools
    
    async def run(self) -> None:
        """Run the agent loop, processing messages from the bus."""
        self._running = True
        await self.workflows.start()
        logger.info("Agent loop started")
        
        while self._running:
            try:
                # Wait for next message
                msg = await asyncio.wait_for(  # 取出待处理的消息
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                
                if msg.channel == "system":
                    asyncio.create_task(self._process_and_publish(msg))
                    continue

                runtime = self._session_runtimes.get(msg.session_key)
                if runtime is None:
                    runtime = SessionRuntime(
                        session_key=msg.session_key,
                        process_message=self._process_message,
                        publish_outbound=self._publish_response,
                    )
                    self._session_runtimes[msg.session_key] = runtime
                await runtime.enqueue(msg)
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        self.workflows.stop()
        for runtime in self._session_runtimes.values():
            runtime.stop()
        logger.info("Agent loop stopping")

    async def _process_and_publish(self, msg: InboundMessage) -> None:
        try:
            response = await self._process_message(msg)
            if response:
                await self._publish_response(response)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            metadata = {"_turn_complete": True} if msg.channel == "websocket" else {}
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=f"Sorry, I encountered an error: {str(e)}",
                metadata=metadata,
            ))

    async def _publish_response(self, response: OutboundMessage) -> None:
        if response.channel == "websocket":
            response.metadata = {
                **(response.metadata or {}),
                "_turn_complete": True,
            }
        await self.bus.publish_outbound(response)

    def _set_tool_contexts(self, channel: str, chat_id: str) -> None:
        """Propagate the active session context to tools that support it."""
        for tool in self.tools.iter_tools():
            set_context = getattr(tool, "set_context", None)
            if callable(set_context):
                set_context(channel, chat_id)

    @staticmethod
    def _looks_like_workflow_submitted_text(content: str) -> bool:
        text = (content or "").strip()
        if not text:
            return False
        lowered = text.lower()
        if "background workflow submitted:" in lowered:
            return True
        if not re.search(r"\bwf_[0-9a-f]{8}\b", lowered):
            return False
        return "workflow" in lowered and "submitted" in lowered

    def _submit_workflow_tool_defs(self) -> list[dict[str, Any]]:
        """Return only the submit_workflow tool definition."""
        submit_defs: list[dict[str, Any]] = []
        for tool_def in self.tools.get_definitions():
            fn = tool_def.get("function")
            if isinstance(fn, dict) and fn.get("name") == "submit_workflow":
                submit_defs.append(tool_def)
        return submit_defs

    async def _retry_submit_workflow_once(
        self,
        *,
        messages: list[dict[str, Any]],
    ) -> tuple[str | None, dict[str, Any], list[str]]:
        """Retry once by forcing a real submit_workflow tool call."""
        submit_tool_defs = self._submit_workflow_tool_defs()
        if not submit_tool_defs:
            return None, {}, []

        retry_messages = list(messages)
        retry_messages.append(
            {
                "role": "user",
                "content": (
                    "Do not output a textual workflow submission confirmation. "
                    "Call the submit_workflow tool now to actually create the workflow."
                ),
            }
        )

        response = await self.provider.chat(
            messages=retry_messages,
            tools=submit_tool_defs,
            model=self.model,
            temperature=self.temperature,
        )
        if not response.has_tool_calls:
            return None, {}, []

        retry_metadata: dict[str, Any] = {}
        retry_tools_used: list[str] = []
        for tool_call in response.tool_calls:
            if tool_call.name != "submit_workflow":
                continue
            retry_tools_used.append(tool_call.name)
            args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
            logger.info(f"Workflow submit retry tool call: {tool_call.name}({args_str[:200]})")
            execution = await self.tools.execute_detailed(tool_call.name, tool_call.arguments)
            if execution.metadata:
                retry_metadata.update(execution.metadata)
            return execution.content, retry_metadata, retry_tools_used
        return None, {}, []

    async def _process_message(self, msg: InboundMessage, session_key: str | None = None) -> OutboundMessage | None:
        """
        Process a single inbound message.
        
        Args:
            msg: The inbound message to process.
            session_key: Override session key (used by process_direct).
        
        Returns:
            The response message, or None if no response needed.
        """
        # Handle system messages (subagent announces)
        # The chat_id contains the original "channel:chat_id" to route back to
        if msg.channel == "system":  # 系统消息判断
            return await self._process_system_message(msg)  # 回报子agent的消息
        
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content  # 日志中输出前80个字
        logger.info(f"Processing message from {msg.channel}:{msg.sender_id}: {preview}")
        
        # Get or create session 获取或创建session
        key = session_key or msg.session_key  # key的格式"{channel}:{chat_id}"，当通过 process_direct() 调用时，会传入自定义值（默认 "cli:direct"）
        session = self.sessions.get_or_create(key)  # 根据key读取或者创建session
        
        # Handle slash commands
        cmd = msg.content.strip().lower()  # 去除间隔和大写，检查是不是特定的命令
        if cmd == "/new":  # 判断是不是开启新对话或者hlep的命令并做相应的处理
            if self.research_mode:
                session.clear()
                # self.sessions.save(session)
                new_session_message = "🌽 New session started."
            else:
                await self._consolidate_memory(session, archive_all=True)  # 巩固记忆
                session.clear()
                self.sessions.save(session)
                new_session_message = "🌽 New session started. Memory consolidated."
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content=new_session_message)
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="🌽 EasyGS commands:\n/new — Start a new conversation\n/help — Show available commands")
        
        # Consolidate memory before processing if session is too large
        if not self.research_mode and len(session.messages) > self.memory_window:  # 如果当前session的消息数量超过记忆窗口了，则利用大模型压缩记忆
            await self._consolidate_memory(session)  # 利用大模型压缩记忆
        
        self._set_tool_contexts(msg.channel, msg.chat_id)
        
        # Build initial messages (use get_history for LLM-formatted messages)
        messages = self.context.build_messages(  # 构建LLM消息列表
            history=session.get_history(),  # 最近的历史消息，（role + content 格式），转化成大模型可接受的格式
            current_message=msg.content,  # 用户本次的输入
            media=msg.media if msg.media else None,  # 是否有多媒体消息
            channel=msg.channel,  # 频道
            chat_id=msg.chat_id,  # chatid
        )
        
        # Agent loop  核心调用！！！！
        iteration = 0
        final_content = None
        final_metadata: dict[str, Any] = {}
        tools_used: list[str] = []
        
        while iteration < self.max_iterations:  # 最多 max_iterations 轮
            iteration += 1
            
            # Call LLM
            response = await self.provider.chat(
                messages=messages,  # 组装好的消息
                tools=self.tools.get_definitions(),  # 所有工具的OpenAI格式的描述
                model=self.model,  # 模型名称
                temperature=self.temperature
            )
            
            # Handle tool calls
            if response.has_tool_calls:  # 判断是否有工具调用
                # Add assistant message with tool calls
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)  # Must be JSON string
                        }
                    }
                    for tc in response.tool_calls  # 对于想调用的每一个工具
                ]
                messages = self.context.add_assistant_message(  # 将 assistant 消息（含 tool_calls）追加到 messages
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )
                
                # Execute tools  逐个执行工具调用
                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)  # 加入使用列表
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)  # 参数
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")  # 调用工具
                    execution = await self.tools.execute_detailed(tool_call.name, tool_call.arguments)
                    result = execution.content
                    messages = self.context.add_tool_result(  # message中增加工具调用的结果
                        messages, tool_call.id, tool_call.name, result
                    )
                    if execution.metadata:
                        final_metadata.update(execution.metadata)
                    if execution.terminal:
                        final_content = result
                        break
                if final_content is not None:
                    break
                # Interleaved CoT: reflect before next action
                messages.append({"role": "user", "content": "Based on the results, either decide next steps or answer the user directly."})  # 向message中追加让大模型进行下一步
                # → 回到 while 循环顶部，带着工具结果再次调用 LLM
            else:
                # No tool calls, we're done  没有使用工具，已经获得了最后的回答
                final_content = response.content
                break
        
        if final_content is None:  # 如果没有得到最终答案，告知用户超出循环次数了或者未收到回应
            if iteration >= self.max_iterations:
                final_content = f"Reached {self.max_iterations} iterations without completion."
            else:
                final_content = "I've completed processing but have no response to give."

        # Guardrail: avoid fake workflow submission text when submit_workflow was never called.
        if (
            self._looks_like_workflow_submitted_text(final_content)
            and "submit_workflow" not in tools_used
        ):
            logger.warning("workflow submit retry triggered: textual submission without submit_workflow call")
            retry_content, retry_metadata, retry_tools_used = await self._retry_submit_workflow_once(
                messages=messages
            )
            if retry_content:
                final_content = retry_content
                if retry_metadata:
                    final_metadata.update(retry_metadata)
                if retry_tools_used:
                    tools_used.extend(retry_tools_used)
                logger.info("workflow submit retry succeeded")
            else:
                final_content = "后台工作流创建失败，请重试。"
                logger.warning("workflow submit retry failed")
        
        # Log response preview
        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content  # 大模型恢复预览
        logger.info(f"Response to {msg.channel}:{msg.sender_id}: {preview}")
        
        # Save to session (include tool names so consolidation sees what happened)  保存session
        session.add_message("user", msg.content)  # 保存用户信息
        session.add_message("assistant", final_content,  # 保存AI回复
                            tools_used=tools_used if tools_used else None)
        self.sessions.save(session)  # → 写入 ~/.easygs/sessions/cli_direct.json
        
        return OutboundMessage(  # 加入到输出队列中
            channel=msg.channel,  # “cli”
            chat_id=msg.chat_id,  # "direct"
            content=final_content,  # AI的最终回答
            metadata={**(msg.metadata or {}), **final_metadata},  # Pass through channel metadata and runtime hints
        )
    
    async def _process_system_message(self, msg: InboundMessage) -> OutboundMessage | None:
        """
        Process a system message (e.g., subagent announce).
        
        The chat_id field contains "original_channel:original_chat_id" to route
        the response back to the correct destination.
        """
        logger.info(f"Processing system message from {msg.sender_id}")
        
        # Parse origin from chat_id (format: "channel:chat_id")
        if ":" in msg.chat_id:
            parts = msg.chat_id.split(":", 1)
            origin_channel = parts[0]  # channel名称
            origin_chat_id = parts[1]  # 聊天ID
        else:
            # Fallback
            origin_channel = "cli"
            origin_chat_id = msg.chat_id
        
        # Use the origin session for context
        session_key = f"{origin_channel}:{origin_chat_id}"  # 产生session—key
        session = self.sessions.get_or_create(session_key)
        metadata = msg.metadata or {}

        if msg.sender_id == "workflow-runner":  # 如果是回报后台工作流执行完成消息的
            response = await self.provider.chat(  # 调用大模型回复后台任务完成消息
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are relaying a background runtime update to the user. "
                            "Summarize only the update in 1-2 short sentences. "
                            "Do not call tools. Do not start new analyses. Do not ask follow-up questions. "
                            "Do not mention unrelated earlier results."
                        ),
                    },
                    {"role": "user", "content": msg.content},
                ],
                model=self.model,
                temperature=0.2,
            )
            final_content = (response.content or "Background task updated.").strip()
            session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
            session.add_message("assistant", final_content)
            self.sessions.save(session)
            await self._maybe_send_completion_email(metadata, final_content)
            outbound_metadata = (
                self._webui_completion_metadata(metadata)
                if origin_channel == "websocket"
                else {}
            )
            return OutboundMessage(  # 组成一条用于返回队列的消息
                channel=origin_channel,
                chat_id=origin_chat_id,
                content=final_content,
                metadata=outbound_metadata,
            )

        self._set_tool_contexts(origin_channel, origin_chat_id)
        
        # Build messages with the announce content
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
            channel=origin_channel,
            chat_id=origin_chat_id,
        )
        
        # Agent loop (limited for announce handling)
        iteration = 0
        final_content = None
        
        while iteration < self.max_iterations:  # 最多调用 max_iterations 次
            iteration += 1
            
            response = await self.provider.chat(  # 调用大模型处理系统消息
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model,
                temperature=self.temperature
            )
            
            if response.has_tool_calls:  # 如果有工具调用，则调用工具，并在message中增加下一步指示请求
                tool_call_dicts = [  # 组织好要调用的工具
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls  # 对于每一个调用的工具
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )
                
                for tool_call in response.tool_calls:  # 依次调用每一个工具
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info(f"Tool call: {tool_call.name}({args_str[:200]})")
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
                # Interleaved CoT: reflect before next action
                messages.append({"role": "user", "content": "Based on the results, either decide next steps or answer the user directly."})
            else:  # 如果没有工具调用，就直接返回大模型调用结果
                final_content = response.content
                break
        
        if final_content is None:
            final_content = "Background task completed."
        
        # Save to session (mark as system message in history)
        session.add_message("user", f"[System: {msg.sender_id}] {msg.content}")
        session.add_message("assistant", final_content)
        self.sessions.save(session)
        
        return OutboundMessage(
            channel=origin_channel,
            chat_id=origin_chat_id,
            content=final_content
        )

    async def _maybe_send_completion_email(self, metadata: dict[str, Any], final_content: str) -> None:
        """Send a completion email without affecting primary channel delivery."""
        if not self.smtp_notifier:
            return

        recipient = self.smtp_notifier.resolve_recipient(
            str(metadata.get("completion_notify_to") or "").strip().lower()
        )
        if not recipient:
            return

        item_id = str(metadata.get("workflow_id") or "").strip()
        label = str(metadata.get("workflow_name") or "").strip()
        status = str(metadata.get("workflow_status") or "").strip()
        kind = "workflow"

        try:
            await self.smtp_notifier.send_workflow_completion(
                label=label,
                status=status,
                summary=final_content,
                workflow_id=item_id,
                to_addr=recipient,
            )
            logger.info(
                "Sent completion email for {} {} to {}",
                kind,
                item_id or "unknown",
                recipient,
            )
        except Exception as e:
            logger.error(
                "Failed to send completion email for {} {} to {}: {}",
                kind,
                item_id or "unknown",
                recipient,
                e,
            )
    
    async def _consolidate_memory(self, session, archive_all: bool = False) -> None:
        """Consolidate old messages into MEMORY.md + HISTORY.md, then trim session."""
        if self.research_mode:  # 在research模式下，不需要压缩
            logger.info("AgentLoop._consolidate_memory skipped because research_mode is enabled: {}", session.key)
            return
        if not session.messages:
            return
        memory = MemoryStore(self.workspace, research_mode=self.research_mode)  # memory处理
        if archive_all:  # 如果归档，就不保留老消息
            old_messages = session.messages
            keep_count = 0
        else:  # 如果不归档，就保留特定数量的老消息
            keep_count = min(10, max(2, self.memory_window // 2))  # 设置保留数量
            old_messages = session.messages[:-keep_count]  # 保留一定旧消息
        if not old_messages:
            return
        logger.info(f"Memory consolidation started: {len(session.messages)} messages, archiving {len(old_messages)}, keeping {keep_count}")

        # Format messages for LLM (include tool names when available)
        lines = []
        for m in old_messages:
            if not m.get("content"):
                continue
            tools = f" [tools: {', '.join(m['tools_used'])}]" if m.get("tools_used") else ""
            lines.append(f"[{m.get('timestamp', '?')[:16]}] {m['role'].upper()}{tools}: {m['content']}")
        conversation = "\n".join(lines)  # 把所有的旧消息都拼接起来
        current_memory = memory.read_long_term()  # 先读现有的记忆

        prompt = f"""You are a memory consolidation agent. Process this conversation and return a JSON object with exactly two keys:

1. "history_entry": A paragraph (2-5 sentences) summarizing the key events/decisions/topics. Start with a timestamp like [YYYY-MM-DD HH:MM]. Include enough detail to be useful when found by grep search later.

2. "memory_update": The updated long-term memory content. Add any new facts: user location, preferences, personal info, habits, project context, technical decisions, tools/services used. If nothing new, return the existing content unchanged.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{conversation}

Respond with ONLY valid JSON, no markdown fences."""

        try:
            response = await self.provider.chat(  # 调用大模型来总结新旧记忆
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )
            text = (response.content or "").strip()  # 获取回复并且去空白
            if text.startswith("```"):  # 处理markdown块的包裹
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(text)

            if entry := result.get("history_entry"):  # := 海象运算符，先赋值再判断是否非空
                memory.append_history(entry)  # 追加到HISTORY.md
            if update := result.get("memory_update"):
                if update != current_memory:  # 写入长期记忆
                    memory.write_long_term(update)

            session.messages = session.messages[-keep_count:] if keep_count else []
            self.sessions.save(session)  # 保存会话
            logger.info(f"Memory consolidation done, session trimmed to {len(session.messages)} messages")
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")

    async def process_direct(  # 构建一个 InboundMessage → 交给 _process_message() 处理
        self,
        content: str,  # 用户输入的内容
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str:
        """
        Process a message directly (for CLI or cron usage).
        
        Args:
            content: The message content.
            session_key: Session identifier (overrides channel:chat_id for session lookup).
            channel: Source channel (for tool context routing).
            chat_id: Source chat ID (for tool context routing).
        
        Returns:
            The agent's response.
        """
        msg = InboundMessage(  # 构建一个InboundMessage
            channel=channel,  # 频道，硬编码了cli
            sender_id="user",  # 硬编码user
            chat_id=chat_id,  # chaID,硬编码了direct
            content=content  # 用户输入的内容
        )
        
        response = await self._process_message(msg, session_key=session_key)  # 核心处理逻辑
        return response.content if response else ""
