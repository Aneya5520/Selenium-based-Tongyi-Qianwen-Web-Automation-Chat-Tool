
"""
通义千问对话爬虫 - 配置管理模块
负责默认配置定义和配置文件加载
"""

import json
import os


# 默认配置
DEFAULT_CONFIG = {
    "headless": False,
    "page_load_timeout": 30,
    "element_wait_timeout": 20,
    "typing_interval": 0.03,
    "response_wait_timeout": 120,
    "save_history": False,
    "history_dir": "chat_history",
    "user_data_dir": None,
}


def get_default_config():
    """返回默认配置的副本"""
    return DEFAULT_CONFIG.copy()


def load_config(config_path=None):
    """
    加载配置

    Args:
        config_path: 配置文件路径(JSON)，为None则返回默认配置

    Returns:
        配置字典
    """
    config = get_default_config()

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                custom_config = json.load(f)
                config.update(custom_config)
        except Exception as e:
            print(f"[!] 加载配置文件失败: {e}")

    return config


def apply_cli_overrides(config, **overrides):
    """
    应用命令行参数覆盖配置

    Args:
        config: 原始配置字典
        **overrides: 需要覆盖的配置项（值为None则跳过）

    Returns:
        更新后的配置字典
    """
    for key, value in overrides.items():
        if value is not None:
            config[key] = value
    return config
