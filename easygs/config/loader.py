"""Configuration loading utilities."""

import json
from pathlib import Path
from typing import Any

from easygs.config.schema import Config


def get_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".easygs" / "config.json"  # 返回 ~/.easygs/config.json 默认路径


def get_data_dir() -> Path:
    """Get the EasyGS data directory."""
    from easygs.utils.helpers import get_data_path
    return get_data_path()


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file or create default.
    
    Args:
        config_path: Optional path to config file. Uses default if not provided.
    
    Returns:
        Loaded configuration object.
    """
    path = config_path or get_config_path()  # 如果不指定配置路径的话，就是～/.easygs/config.yaml的默认路径
    
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)  # 读取文件并解析成python字典
            data = _migrate_config(data)  # 迁移旧配置
            return Config.model_validate(convert_keys(data))  # 根据加载的配置，验证并创建Config实例
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            print("Using default configuration.")
    
    return Config()  # 如果配置不存在，返回空的配置对象


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save.
        config_path: Optional path to save to. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to camelCase format
    data = config.model_dump()  # 将模型实例转化为字典
    data = convert_to_camel(data)  # 键名转化为驼峰命名
    
    with open(path, "w") as f:  # 以json形式保存，2空格缩进
        json.dump(data, f, indent=2)


def _migrate_config(data: dict) -> dict:  # 向后兼容旧版本配置，将旧的配置迁移到新的配置路径，data就是配置字典
    """Migrate old config formats to current."""
    # Move tools.exec.restrictToWorkspace → tools.restrictToWorkspace
    tools = data.get("tools", {})  # 旧格式:tools.exec.restrictToWorkspace
    exec_cfg = tools.get("exec", {})  # 新格式：tools.restrictToWorkspace 
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")

    # Move standalone completion-notify settings out of channels.email.
    channels = data.get("channels", {})
    email_cfg = channels.get("email", {})
    notify_cfg = data.get("emailOnlyNotify")
    legacy_notify_to = email_cfg.get("completionNotifyTo")
    if legacy_notify_to and not notify_cfg:
        data["emailOnlyNotify"] = {
            "enabled": True,
            "smtpHost": email_cfg.get("smtpHost", ""),
            "smtpPort": email_cfg.get("smtpPort", 587),
            "smtpUsername": email_cfg.get("smtpUsername", ""),
            "smtpPassword": email_cfg.get("smtpPassword", ""),
            "smtpUseTls": email_cfg.get("smtpUseTls", True),
            "smtpUseSsl": email_cfg.get("smtpUseSsl", False),
            "fromAddress": email_cfg.get("fromAddress", ""),
            "toAddress": legacy_notify_to,
        }
        email_cfg.pop("completionNotifyTo", None)
    return data  # 如果旧格式有但新格式没有，就迁移到新格式


def convert_keys(data: Any) -> Any:  # 键名格式转换，将驼峰命名转为python的下划线命名
    """Convert camelCase keys to snake_case for Pydantic."""
    if isinstance(data, dict):
        return {camel_to_snake(k): convert_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_keys(item) for item in data]
    return data


def convert_to_camel(data: Any) -> Any:
    """Convert snake_case keys to camelCase."""
    if isinstance(data, dict):
        return {snake_to_camel(k): convert_to_camel(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_camel(item) for item in data]
    return data


def camel_to_snake(name: str) -> str:  # 驼峰命名转化为下划线命名，找到大写字母就加下划线
    """Convert camelCase to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
