"""Configuration module for easygs."""

from easygs.config.loader import load_config, get_config_path
from easygs.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]
