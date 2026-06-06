"""CLI commands for EasyGS."""

import asyncio
import json
import os
import signal
from datetime import datetime
from pathlib import Path
import select
import sys
from contextlib import contextmanager

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout

from easygs import __version__, __logo__

app = typer.Typer(  # 创建 Typer CLI 应用实例，用于构建easygs的命令行界面，后续会通过@app.command()装饰器注册各种子命令
    name="EasyGS",  #   应用名称，用于 --help 显示
    help=f"{__logo__} EasyGS - An LLM Agent For Genomic Selection",  #   帮助文本（硬编码）
    no_args_is_help=True,  #   无参数时自动显示帮助
)

console = Console()  # 创建 rich Console 实例，用于终端彩色输出
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}

# ---------------------------------------------------------------------------
# CLI input: prompt_toolkit for editing, paste, history, and display
# ---------------------------------------------------------------------------

_PROMPT_SESSION: PromptSession | None = None
_SAVED_TERM_ATTRS = None  # original termios settings, restored on exit


@contextmanager
def _gateway_instance_lock(lock_path: Path, *, port: int):
    """Ensure only one gateway instance is running at a time."""
    import fcntl

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            lock_file.seek(0)
            raw = lock_file.read().strip()
            details = {}
            if raw:
                try:
                    details = json.loads(raw)
                except json.JSONDecodeError:
                    details = {}

            console.print("[red]Another EasyGS gateway is already running.[/red]")
            pid = details.get("pid")
            if pid:
                console.print(f"[yellow]PID:[/yellow] {pid}")
            started_at = details.get("started_at")
            if started_at:
                console.print(f"[yellow]Started at:[/yellow] {started_at}")
            existing_port = details.get("port")
            if existing_port:
                console.print(f"[yellow]Port:[/yellow] {existing_port}")
            console.print("Please stop the existing gateway before starting a new one.")
            raise typer.Exit(1) from exc

        payload = {
            "pid": os.getpid(),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "port": port,
            "command": " ".join(sys.argv),
        }
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(json.dumps(payload))
        lock_file.flush()
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        lock_file.close()


def _flush_pending_tty_input() -> None:
    """Drop unread keypresses typed while the model was generating output."""
    try:
        fd = sys.stdin.fileno()
        if not os.isatty(fd):
            return
    except Exception:
        return

    try:
        import termios
        termios.tcflush(fd, termios.TCIFLUSH)
        return
    except Exception:
        pass

    try:
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if not ready:
                break
            if not os.read(fd, 4096):
                break
    except Exception:
        return


def _restore_terminal() -> None:
    """Restore terminal to its original state (echo, line buffering, etc.)."""
    if _SAVED_TERM_ATTRS is None:
        return
    try:
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _SAVED_TERM_ATTRS)
    except Exception:
        pass


def _init_prompt_session() -> None:  # 初始化交互式命令行对话
    """Create the prompt_toolkit session with persistent file history."""
    global _PROMPT_SESSION, _SAVED_TERM_ATTRS

    # Save terminal state so we can restore it on exit  保存终端状态，程序退出时可恢复
    try:
        import termios
        _SAVED_TERM_ATTRS = termios.tcgetattr(sys.stdin.fileno())
    except Exception:
        pass

    history_file = Path.home() / ".easygs" / "history" / "cli_history"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    _PROMPT_SESSION = PromptSession(  # 创建 prompt_toolkit 会话
        history=FileHistory(str(history_file)),  # 使用文件存储历史记录
        enable_open_in_editor=False,
        multiline=False,   # Enter submits (single line mode)
    )


def _print_agent_response(response: str, render_markdown: bool) -> None:
    """Render assistant response with consistent terminal styling."""
    content = response or ""
    body = Markdown(content) if render_markdown else Text(content)
    console.print()
    console.print(f"[cyan]{__logo__} EasyGS[/cyan]")
    console.print(body)  # 输出结果
    console.print()


def _print_research_mode_notice(research_mode: bool) -> None:
    """Show the current operating mode in the terminal."""
    if research_mode:
        console.print(
            "[green]✓ Current mode: Research Mode \n"
            "If you want to use EasyGS analysis tools, please keep this mode. \n"
            "If you just want to chat, switching to Daily Mode is recommended. [/green]"
        )
    else:
        console.print(
            "[yellow]Warning: Current mode: Daily Mode. \n"
            "This may affect skills and tool calls. \n"
            "If you want to use EasyGS analysis tools, switching to Research Mode is recommended. [/yellow]"
        )


def _is_exit_command(command: str) -> bool:
    """Return True when input should end interactive chat."""
    return command.lower() in EXIT_COMMANDS


async def _read_interactive_input_async() -> str:
    """Read user input using prompt_toolkit (handles paste, history, display).

    prompt_toolkit natively handles:
    - Multiline paste (bracketed paste mode)
    - History navigation (up/down arrows)
    - Clean display (no ghost characters or artifacts)
    """
    if _PROMPT_SESSION is None:
        raise RuntimeError("Call _init_prompt_session() first")
    try:
        with patch_stdout():
            return await _PROMPT_SESSION.prompt_async(
                HTML("<b fg='ansiblue'>You:</b> "),
            )
    except EOFError as exc:
        raise KeyboardInterrupt from exc



def version_callback(value: bool):
    if value:
        console.print(f"{__logo__} EasyGS v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    """EasyGS - Personal AI Assistant."""
    pass


# ============================================================================
# Onboard / Setup
# ============================================================================

# CLI入口注册
@app.command()  # 注册为 typer 子命令：easygs onboard
def onboard():  # 初始化用户的easygs配置和工作区
    """Initialize EasyGS configuration and workspace."""
    from easygs.config.loader import get_config_path, get_data_dir, load_config, save_config
    from easygs.config.schema import Config
    from easygs.resources import resolve_user_resource_path, resolve_user_resources_root
    from easygs.utils.helpers import get_workspace_path  # 延迟导入必需模块，避免未使用时加载无关依赖，加快CLI启动速度
    
    config_path = get_config_path()  # 获取默认配置路径
    
    if config_path.exists():  # 检查配置是否存在，如果存在了，询问是否覆盖
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
        console.print("  [bold]y[/bold] = overwrite with defaults (existing values will be lost)")
        console.print("  [bold]N[/bold] = refresh config, keeping existing values and adding new fields")
        if typer.confirm("Overwrite?"):
            config = Config()  # 配置
            save_config(config)  # 保存配置
            console.print(f"[green]✓[/green] Config reset to defaults at {config_path}")
        else:  # 如果不覆盖，加载现有配置然后再保存
            config = load_config()
            save_config(config)
            console.print(f"[green]✓[/green] Config refreshed at {config_path} (existing values preserved)")
    else:  # 如果没有存在，创建新的配置文件
        save_config(Config())
        console.print(f"[green]✓[/green] Created config at {config_path}")
    
    # Create workspace
    workspace = get_workspace_path()  # workspace 表示文件系统路径，是Path类型的
    
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created workspace at {workspace}")

    run_dir = get_data_dir() / "run"
    if not run_dir.exists():
        run_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created runtime directory at {run_dir}")

    resources_root = resolve_user_resources_root()
    if not resources_root.exists():
        resources_root.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created resources directory at {resources_root}")

    pfam_resource_dir = resolve_user_resource_path("pfam_enrichment_analysis")
    if not pfam_resource_dir.exists():
        pfam_resource_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓[/green] Created PFAM resources directory at {pfam_resource_dir}")
    
    # Create default bootstrap files  创建工作区的一系列模板文件
    _create_workspace_templates(workspace)
    
    console.print(f"\n{__logo__} EasyGS is ready!")
    console.print("\nNext steps:")
    console.print("  1. Add your API key to [cyan]~/.easygs/config.json[/cyan]")
    console.print("     Get one at: https://openrouter.ai/keys")
    console.print("  2. Chat: [cyan]easygs agent -m \"Hello!\"[/cyan]")
    console.print("\n[dim]Want Telegram/WhatsApp? See the project docs for chat app setup.[/dim]")



# 创建默认的工作区模板文件
def _create_workspace_templates(workspace: Path):
    """Create default workspace template files."""
    # AGENTS.md，提供给 LLM 的系统指令（build_system_prompt 会读取
    templates = {  # 字典中保存文件名和文件内容
        "AGENTS.md": """# Agent Instructions

You are a helpful AI assistant. Be concise, accurate, and friendly.

## Guidelines

- Always explain what you're doing before taking actions
- Ask for clarification when the request is ambiguous
- Use tools to help accomplish tasks
- Remember important information in memory/MEMORY.md; past events are logged in memory/HISTORY.md
""",
        "SOUL.md": """# Soul

I am EasyGS, a lightweight AI assistant.

## Personality

- Helpful and friendly
- Concise and to the point
- Curious and eager to learn

## Values

- Accuracy over speed
- User privacy and safety
- Transparency in actions
""",
        "USER.md": """# User

Information about the user goes here.

## Preferences

- Communication style: (casual/formal)
- Timezone: (your timezone)
- Language: (your preferred language)
""",
    }
    # 对于每个文件名，写入文件内容
    for filename, content in templates.items():  
        file_path = workspace / filename
        if not file_path.exists():
            file_path.write_text(content)
            console.print(f"  [dim]Created {filename}[/dim]")
    
    # Create memory directory and MEMORY.md
    memory_dir = workspace / "memory"  # 创建memory文件夹
    memory_dir.mkdir(exist_ok=True)
    memory_file = memory_dir / "MEMORY.md"
    if not memory_file.exists():
        memory_file.write_text("""# Long-term Memory

This file stores important information that should persist across sessions.

## User Information

(Important facts about the user)

## Preferences

(User preferences learned over time)

## Important Notes

(Things to remember)
""")
        console.print("  [dim]Created memory/MEMORY.md[/dim]")
    # 在memory文件夹中写入HISTORY.md
    history_file = memory_dir / "HISTORY.md"
    if not history_file.exists():
        history_file.write_text("")
        console.print("  [dim]Created memory/HISTORY.md[/dim]")

    # Create skills directory for custom user skills  创建skills文件夹
    skills_dir = workspace / "skills"
    skills_dir.mkdir(exist_ok=True)


def _make_provider(config):  # 根据配置创建LLM提供商实例
    """Create LiteLLMProvider from config. Exits if no API key found."""
    from easygs.providers.litellm_provider import LiteLLMProvider
    p = config.get_provider()
    model = config.agents.defaults.model
    if not (p and p.api_key) and not model.startswith("bedrock/"):
        console.print("[red]Error: No API key configured.[/red]")
        console.print("Set one in ~/.easygs/config.json under providers section")
        raise typer.Exit(1)
    return LiteLLMProvider(  # littlellm调用类
        api_key=p.api_key if p else None,
        api_base=config.get_api_base(),
        default_model=model,
        extra_headers=p.extra_headers if p else None,
        provider_name=config.get_provider_name(),
    )


def _make_smtp_notifier(config):
    """Create the standalone SMTP notifier from its dedicated config."""
    from easygs.notifications.smtp import SmtpNotifier

    return SmtpNotifier.from_notify_config(config.email_only_notify)


# ============================================================================
# Gateway / Server
# ============================================================================


@app.command()  # 使用Typer装饰器，将gateway注册为一个CLI子命令
def gateway(
    port: int = typer.Option(18790, "--port", "-p", help="Gateway port"),  # 端口，可用-p覆盖
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),  # 是否启用DEBUG日志，可用-v覆盖
    research_mode: bool = typer.Option(True, "--research-mode/--daily-mode", help="Research mode may skip session persistence, memory writes, and consolidation"),
):
    """Start the EasyGS gateway."""
    from easygs.config.loader import load_config, get_data_dir  # 延迟导入所有依赖模块，在函数执行时才导入，避免模块加载时的问题
    from easygs.bus.queue import MessageBus
    from easygs.agent.loop import AgentLoop
    from easygs.channels.manager import ChannelManager
    from easygs.session.manager import SessionManager
    from easygs.cron.service import CronService
    from easygs.cron.types import CronJob
    from easygs.heartbeat.service import HeartbeatService
    
    if verbose:  # 根据verbose参数启用调试日志
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    lock_path = get_data_dir() / "run" / "gateway.lock"
    with _gateway_instance_lock(lock_path, port=port):
        console.print(f"{__logo__} Starting EasyGS gateway on port {port}...")
        console.print(f"[dim]Gateway PID: {os.getpid()}[/dim]")
        _print_research_mode_notice(research_mode)
        
        config = load_config()  # 加载配置文件 ～/.easygs/config.json
        bus = MessageBus()  # 创建消息总线，初始化两个异步队列：inbound（渠道→Agent）和 outbound（Agent→渠道）
        provider = _make_provider(config)  # 创建LLM提供商实例
        smtp_notifier = _make_smtp_notifier(config)
        session_manager = SessionManager(
            config.workspace_path,
            research_mode=research_mode,
        )  # 会话管理器
        
        # Create cron service first (callback set after agent creation)
        cron_store_path = get_data_dir() / "cron" / "jobs.json"  # 创建定时任务服务
        cron = CronService(cron_store_path)
        
        # Create agent with cron service  创建Agent核心循环
        agent = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=config.workspace_path,
            model=config.agents.defaults.model,
            temperature=config.agents.defaults.temperature,
            max_iterations=config.agents.defaults.max_tool_iterations,
            memory_window=config.agents.defaults.memory_window,
            brave_api_key=config.tools.web.search.api_key or None,
            exec_config=config.tools.exec,
            cron_service=cron,
            restrict_to_workspace=config.tools.restrict_to_workspace,
            session_manager=session_manager,
            research_mode=research_mode,
            smtp_notifier=smtp_notifier,
        )
        
        # Set cron callback (needs agent)  设置定时人物回调
        async def on_cron_job(job: CronJob) -> str | None:
            """Execute a cron job through the agent."""
            response = await agent.process_direct(  # 调用Agent处理定时任务的消息内容
                job.payload.message,  # 定时人物的消息内容
                session_key=f"cron:{job.id}",  # 会话标识：cron:任务ID
                channel=job.payload.channel or "cli",  # 通道，默认cli
                chat_id=job.payload.to or "direct",  # 聊天ID,默认direct
            )
            if job.payload.deliver and job.payload.to:  
                from easygs.bus.events import OutboundMessage
                await bus.publish_outbound(OutboundMessage(
                    channel=job.payload.channel or "cli",
                    chat_id=job.payload.to,
                    content=response or ""
                ))
            return response
        cron.on_job = on_cron_job
        
        # Create heartbeat service  创建心跳服务及回调
        async def on_heartbeat(prompt: str) -> str:  # async用于定义异步函数，遇到阻塞时让出控制权
            """Execute heartbeat through the agent."""
            return await agent.process_direct(prompt, session_key="heartbeat")  # await标识等待这个操作完成，期间可以做别的
        
        heartbeat = HeartbeatService(  # 创建一个心跳服务，每30分钟自动调用一次
            workspace=config.workspace_path,
            on_heartbeat=on_heartbeat,
            interval_s=30 * 60,  # 30 minutes  硬编码30分钟，未从配置中读取
            enabled=True
        )
        
        # Create channel manager  创建频道管理器
        channels = ChannelManager(config, bus, session_manager=session_manager)
        
        if channels.enabled_channels:  # 输出启用的频道列表
            console.print(f"[green]✓[/green] Channels enabled: {', '.join(channels.enabled_channels)}")
            if "websocket" in channels.enabled_channels:
                ws_config = config.channels.websocket
                scheme = "https" if ws_config.ssl_certfile and ws_config.ssl_keyfile else "http"
                display_host = "127.0.0.1" if ws_config.host in {"0.0.0.0", "::"} else ws_config.host
                console.print(
                    f"[green]✓[/green] WebUI: {scheme}://{display_host}:{ws_config.port}"
                )
        else:
            console.print("[yellow]Warning: No channels enabled[/yellow]")
        
        cron_status = cron.status()
        if cron_status["jobs"] > 0:  # 输出定时任务的数量
            console.print(f"[green]✓[/green] Cron: {cron_status['jobs']} scheduled jobs")
        
        console.print(f"[green]✓[/green] Heartbeat: every 30m")
        
        async def run():  # 启动主事件循环，async标识异步
            try:
                await cron.start()  # 等待启动定时任务服务
                await heartbeat.start()  # 等待启动心跳服务
                await asyncio.gather(  # 并发启动两个异步任务
                    agent.run(),  # 启动agent主循环
                    channels.start_all(),  # 启动所有频道
                )
            except KeyboardInterrupt:
                console.print("\nShutting down...")
                heartbeat.stop()
                cron.stop()
                agent.stop()
                await channels.stop_all()
        
        asyncio.run(run())  # 启动整个异步事件循环




# ============================================================================
# Agent Commands
# ============================================================================


@app.command()  # 注册为 typer 子命令：easygs agent
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send to the agent"),  # 来源于命令行-m参数
    session_id: str = typer.Option("cli:direct", "--session", "-s", help="Session ID"),  # 来源于命令行-s参数，默认cli:default
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", help="Render assistant output as Markdown"),
    logs: bool = typer.Option(False, "--logs/--no-logs", help="Show EasyGS runtime logs during chat"),
    research_mode: bool = typer.Option(True, "--research-mode/--daily-mode", help="Skip session persistence, memory writes, and consolidation"),
):
    """Interact with the agent directly."""
    from easygs.config.loader import load_config  # 延迟导入，提升加载速度
    from easygs.bus.queue import MessageBus
    from easygs.agent.loop import AgentLoop
    from loguru import logger
    
    config = load_config()  # 从配置文件中加载配置
    
    bus = MessageBus()  # 创建message bus
    provider = _make_provider(config)  # 创建littlellm调用类
    smtp_notifier = _make_smtp_notifier(config)

    if logs:  # 是否显示日志
        logger.enable("easygs")
    else:
        logger.disable("easygs")
    
    agent_loop = AgentLoop(  # 创建代理循环
        bus=bus,  # 异步消息队列
        provider=provider,  # 大模型提供调用
        workspace=config.workspace_path,  # 工作空间
        model=config.agents.defaults.model,  # 模型名
        max_iterations=config.agents.defaults.max_tool_iterations,
        temperature=config.agents.defaults.temperature,
        memory_window=config.agents.defaults.memory_window,
        brave_api_key=config.tools.web.search.api_key or None,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        research_mode=research_mode,
        smtp_notifier=smtp_notifier,
    )
    
    # Show spinner when logs are off (no output to miss); skip when logs are on
    def _thinking_ctx():
        if logs:  # 输出日志无动画
            from contextlib import nullcontext
            return nullcontext()
        # Animated spinner is safe to use with prompt_toolkit input handling
        return console.status("[dim]EasyGS is thinking...[/dim]", spinner="dots")  # 输出动画无日志

    if message:  # 单消息模式
        # Single message mode
        async def run_once():  # 定义
            with _thinking_ctx():
                response = await agent_loop.process_direct(message, session_id)  # 核心调用
            _print_agent_response(response, render_markdown=markdown)  # 打印结果
        
        asyncio.run(run_once())  # 启动事件循环 → 执行协程 → 等完成 → 退出
    else:  # 当未使用-m参数的时候，进入交互模式
        # Interactive mode
        _init_prompt_session()
        console.print(f"{__logo__} Interactive mode (type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit)\n")
        _print_research_mode_notice(research_mode)
        console.print()

        def _exit_on_sigint(signum, frame):
            _restore_terminal()
            console.print("\nGoodbye!")
            os._exit(0)

        signal.signal(signal.SIGINT, _exit_on_sigint)
        
        async def run_interactive():
            while True:  # 无限循环
                try:
                    _flush_pending_tty_input()
                    user_input = await _read_interactive_input_async()  # 等待用户输入
                    command = user_input.strip()
                    if not command:  # 跳过空输入
                        continue

                    if _is_exit_command(command):  # 如果用户输入退出指令就退出
                        _restore_terminal()
                        console.print("\nGoodbye!")
                        break
                    
                    with _thinking_ctx():
                        response = await agent_loop.process_direct(user_input, session_id)  # 核心调用
                    _print_agent_response(response, render_markdown=markdown)
                except KeyboardInterrupt:
                    _restore_terminal()
                    console.print("\nGoodbye!")
                    break
                except EOFError:
                    _restore_terminal()
                    console.print("\nGoodbye!")
                    break
        
        asyncio.run(run_interactive())  # 启动事件循环


# ============================================================================
# Channel Commands
# ============================================================================


channels_app = typer.Typer(help="Manage channels")
app.add_typer(channels_app, name="channels")


@channels_app.command("status")
def channels_status():
    """Show channel status."""
    from easygs.config.loader import load_config

    config = load_config()

    table = Table(title="Channel Status")
    table.add_column("Channel", style="cyan")
    table.add_column("Enabled", style="green")
    table.add_column("Configuration", style="yellow")

    # WhatsApp
    wa = config.channels.whatsapp
    table.add_row(
        "WhatsApp",
        "✓" if wa.enabled else "✗",
        wa.bridge_url
    )

    dc = config.channels.discord
    table.add_row(
        "Discord",
        "✓" if dc.enabled else "✗",
        dc.gateway_url
    )

    # Feishu
    fs = config.channels.feishu
    fs_config = f"app_id: {fs.app_id[:10]}..." if fs.app_id else "[dim]not configured[/dim]"
    table.add_row(
        "Feishu",
        "✓" if fs.enabled else "✗",
        fs_config
    )

    # Mochat
    mc = config.channels.mochat
    mc_base = mc.base_url or "[dim]not configured[/dim]"
    table.add_row(
        "Mochat",
        "✓" if mc.enabled else "✗",
        mc_base
    )
    
    # Telegram
    tg = config.channels.telegram
    tg_config = f"token: {tg.token[:10]}..." if tg.token else "[dim]not configured[/dim]"
    table.add_row(
        "Telegram",
        "✓" if tg.enabled else "✗",
        tg_config
    )

    # Slack
    slack = config.channels.slack
    slack_config = "socket" if slack.app_token and slack.bot_token else "[dim]not configured[/dim]"
    table.add_row(
        "Slack",
        "✓" if slack.enabled else "✗",
        slack_config
    )

    console.print(table)


def _get_bridge_dir() -> Path:
    """Get the bridge directory, setting it up if needed."""
    import shutil
    import subprocess
    
    # User's bridge location
    user_bridge = Path.home() / ".easygs" / "bridge"
    
    # Check if already built
    if (user_bridge / "dist" / "index.js").exists():
        return user_bridge
    
    # Check for npm
    if not shutil.which("npm"):
        console.print("[red]npm not found. Please install Node.js >= 18.[/red]")
        raise typer.Exit(1)
    
    # Find source bridge: first check package data, then source dir
    pkg_bridge = Path(__file__).parent.parent / "bridge"  # easygs/bridge (installed)
    src_bridge = Path(__file__).parent.parent.parent / "bridge"  # repo root/bridge (dev)
    
    source = None
    if (pkg_bridge / "package.json").exists():
        source = pkg_bridge
    elif (src_bridge / "package.json").exists():
        source = src_bridge
    
    if not source:
        console.print("[red]Bridge source not found.[/red]")
        console.print("Try reinstalling: pip install --force-reinstall easygs")
        raise typer.Exit(1)
    
    console.print(f"{__logo__} Setting up bridge...")
    
    # Copy to user directory
    user_bridge.parent.mkdir(parents=True, exist_ok=True)
    if user_bridge.exists():
        shutil.rmtree(user_bridge)
    shutil.copytree(source, user_bridge, ignore=shutil.ignore_patterns("node_modules", "dist"))
    
    # Install and build
    try:
        console.print("  Installing dependencies...")
        subprocess.run(["npm", "install"], cwd=user_bridge, check=True, capture_output=True)
        
        console.print("  Building...")
        subprocess.run(["npm", "run", "build"], cwd=user_bridge, check=True, capture_output=True)
        
        console.print("[green]✓[/green] Bridge ready\n")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Build failed: {e}[/red]")
        if e.stderr:
            console.print(f"[dim]{e.stderr.decode()[:500]}[/dim]")
        raise typer.Exit(1)
    
    return user_bridge


@channels_app.command("login")
def channels_login():
    """Link device via QR code."""
    import subprocess
    from easygs.config.loader import load_config
    
    config = load_config()
    bridge_dir = _get_bridge_dir()
    
    console.print(f"{__logo__} Starting bridge...")
    console.print("Scan the QR code to connect.\n")
    
    env = {**os.environ}
    if config.channels.whatsapp.bridge_token:
        env["BRIDGE_TOKEN"] = config.channels.whatsapp.bridge_token
    
    try:
        subprocess.run(["npm", "start"], cwd=bridge_dir, check=True, env=env)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Bridge failed: {e}[/red]")
    except FileNotFoundError:
        console.print("[red]npm not found. Please install Node.js.[/red]")


# ============================================================================
# Cron Commands
# ============================================================================

cron_app = typer.Typer(help="Manage scheduled tasks")
app.add_typer(cron_app, name="cron")

workflows_app = typer.Typer(help="Inspect background workflows")
app.add_typer(workflows_app, name="workflows")


@cron_app.command("list")
def cron_list(
    all: bool = typer.Option(False, "--all", "-a", help="Include disabled jobs"),
):
    """List scheduled jobs."""
    from easygs.config.loader import get_data_dir
    from easygs.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    jobs = service.list_jobs(include_disabled=all)
    
    if not jobs:
        console.print("No scheduled jobs.")
        return
    
    table = Table(title="Scheduled Jobs")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Schedule")
    table.add_column("Status")
    table.add_column("Next Run")
    
    import time
    for job in jobs:
        # Format schedule
        if job.schedule.kind == "every":
            sched = f"every {(job.schedule.every_ms or 0) // 1000}s"
        elif job.schedule.kind == "cron":
            sched = job.schedule.expr or ""
        else:
            sched = "one-time"
        
        # Format next run
        next_run = ""
        if job.state.next_run_at_ms:
            next_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(job.state.next_run_at_ms / 1000))
            next_run = next_time
        
        status = "[green]enabled[/green]" if job.enabled else "[dim]disabled[/dim]"
        
        table.add_row(job.id, job.name, sched, status, next_run)
    
    console.print(table)


@cron_app.command("add")
def cron_add(
    name: str = typer.Option(..., "--name", "-n", help="Job name"),
    message: str = typer.Option(..., "--message", "-m", help="Message for agent"),
    every: int = typer.Option(None, "--every", "-e", help="Run every N seconds"),
    cron_expr: str = typer.Option(None, "--cron", "-c", help="Cron expression (e.g. '0 9 * * *')"),
    at: str = typer.Option(None, "--at", help="Run once at time (ISO format)"),
    deliver: bool = typer.Option(False, "--deliver", "-d", help="Deliver response to channel"),
    to: str = typer.Option(None, "--to", help="Recipient for delivery"),
    channel: str = typer.Option(None, "--channel", help="Channel for delivery (e.g. 'telegram', 'whatsapp')"),
):
    """Add a scheduled job."""
    from easygs.config.loader import get_data_dir
    from easygs.cron.service import CronService
    from easygs.cron.types import CronSchedule
    
    # Determine schedule type
    if every:
        schedule = CronSchedule(kind="every", every_ms=every * 1000)
    elif cron_expr:
        schedule = CronSchedule(kind="cron", expr=cron_expr)
    elif at:
        import datetime
        dt = datetime.datetime.fromisoformat(at)
        schedule = CronSchedule(kind="at", at_ms=int(dt.timestamp() * 1000))
    else:
        console.print("[red]Error: Must specify --every, --cron, or --at[/red]")
        raise typer.Exit(1)
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    job = service.add_job(
        name=name,
        schedule=schedule,
        message=message,
        deliver=deliver,
        to=to,
        channel=channel,
    )
    
    console.print(f"[green]✓[/green] Added job '{job.name}' ({job.id})")


@cron_app.command("remove")
def cron_remove(
    job_id: str = typer.Argument(..., help="Job ID to remove"),
):
    """Remove a scheduled job."""
    from easygs.config.loader import get_data_dir
    from easygs.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    if service.remove_job(job_id):
        console.print(f"[green]✓[/green] Removed job {job_id}")
    else:
        console.print(f"[red]Job {job_id} not found[/red]")


@cron_app.command("enable")
def cron_enable(
    job_id: str = typer.Argument(..., help="Job ID"),
    disable: bool = typer.Option(False, "--disable", help="Disable instead of enable"),
):
    """Enable or disable a job."""
    from easygs.config.loader import get_data_dir
    from easygs.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    job = service.enable_job(job_id, enabled=not disable)
    if job:
        status = "disabled" if disable else "enabled"
        console.print(f"[green]✓[/green] Job '{job.name}' {status}")
    else:
        console.print(f"[red]Job {job_id} not found[/red]")


@cron_app.command("run")
def cron_run(
    job_id: str = typer.Argument(..., help="Job ID to run"),
    force: bool = typer.Option(False, "--force", "-f", help="Run even if disabled"),
):
    """Manually run a job."""
    from easygs.config.loader import get_data_dir
    from easygs.cron.service import CronService
    
    store_path = get_data_dir() / "cron" / "jobs.json"
    service = CronService(store_path)
    
    async def run():
        return await service.run_job(job_id, force=force)
    
    if asyncio.run(run()):
        console.print(f"[green]✓[/green] Job executed")
    else:
        console.print(f"[red]Failed to run job {job_id}[/red]")


@workflows_app.command("list")
def workflows_list(
    status: str = typer.Option("all", "--status", "-s", help="Filter by status: all, queued, running, succeeded, failed, cancelled"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of workflows to show"),
):
    """List background workflows and their current statuses."""
    from easygs.config.loader import get_data_dir
    from easygs.bus.queue import MessageBus
    from easygs.workflows.service import WorkflowService

    service = WorkflowService(
        store_path=get_data_dir() / "workflows" / "workflows.db",
        bus=MessageBus(),
        workspace=get_data_dir(),
        mark_interrupted=False,
    )
    console.print(service.format_listing(status=status, limit=limit))


@workflows_app.command("status")
def workflows_status(
    workflow_id: str = typer.Argument(..., help="Workflow ID to inspect"),
):
    """Show status for a background workflow."""
    from easygs.config.loader import get_data_dir
    from easygs.bus.queue import MessageBus
    from easygs.workflows.service import WorkflowService

    service = WorkflowService(
        store_path=get_data_dir() / "workflows" / "workflows.db",
        bus=MessageBus(),
        workspace=get_data_dir(),
        mark_interrupted=False,
    )
    console.print(service.format_status(workflow_id))


@workflows_app.command("result")
def workflows_result(
    workflow_id: str = typer.Argument(..., help="Workflow ID to inspect"),
):
    """Show final result for a background workflow."""
    from easygs.config.loader import get_data_dir
    from easygs.bus.queue import MessageBus
    from easygs.workflows.service import WorkflowService

    service = WorkflowService(
        store_path=get_data_dir() / "workflows" / "workflows.db",
        bus=MessageBus(),
        workspace=get_data_dir(),
        mark_interrupted=False,
    )
    console.print(service.format_result(workflow_id))


@workflows_app.command("cancel")
def workflows_cancel(
    workflow_id: str = typer.Argument(..., help="Workflow ID to cancel"),
    reason: str = typer.Option("", "--reason", "-r", help="Optional cancellation reason"),
):
    """Cancel a queued or running background workflow."""
    from easygs.config.loader import get_data_dir
    from easygs.bus.queue import MessageBus
    from easygs.workflows.service import WorkflowService

    service = WorkflowService(
        store_path=get_data_dir() / "workflows" / "workflows.db",
        bus=MessageBus(),
        workspace=get_data_dir(),
        mark_interrupted=False,
    )
    console.print(asyncio.run(service.cancel_workflow(workflow_id, reason=reason or None)))


# ============================================================================
# Status Commands
# ============================================================================


@app.command()
def status():
    """Show EasyGS status."""
    from easygs.config.loader import load_config, get_config_path
    from easygs.resources import resolve_user_resources_root

    config_path = get_config_path()
    config = load_config()
    workspace = config.workspace_path
    resources_root = resolve_user_resources_root()

    console.print(f"{__logo__} EasyGS Status\n")

    console.print(f"Config: {config_path} {'[green]✓[/green]' if config_path.exists() else '[red]✗[/red]'}")
    console.print(f"Workspace: {workspace} {'[green]✓[/green]' if workspace.exists() else '[red]✗[/red]'}")
    console.print(f"Resources: {resources_root} {'[green]✓[/green]' if resources_root.exists() else '[red]✗[/red]'}")

    if config_path.exists():
        from easygs.providers.registry import PROVIDERS

        console.print(f"Model: {config.agents.defaults.model}")
        
        # Check API keys from registry
        for spec in PROVIDERS:
            p = getattr(config.providers, spec.name, None)
            if p is None:
                continue
            if spec.is_local:
                # Local deployments show api_base instead of api_key
                if p.api_base:
                    console.print(f"{spec.label}: [green]✓ {p.api_base}[/green]")
                else:
                    console.print(f"{spec.label}: [dim]not set[/dim]")
            else:
                has_key = bool(p.api_key)
                console.print(f"{spec.label}: {'[green]✓[/green]' if has_key else '[dim]not set[/dim]'}")


if __name__ == "__main__":
    app()
