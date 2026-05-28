
"""
通义千问对话爬虫 - 自动驱动版
使用webdriver-manager自动管理ChromeDriver，无需手动下载

模块结构:
    - config: 配置管理（默认配置、加载配置）
    - browser: 浏览器管理（Chrome初始化、反检测）
    - hooks: JS Hook脚本和网络拦截
    - page_interactor: 页面交互（查找元素、发送消息）
    - response_parser: 响应解析（DOM解析、多策略提取）
    - chat_manager: 对话管理（核心业务逻辑）
    - cli: 命令行入口
"""

from .chat_manager import QianWenChatAuto
from .config import get_default_config, load_config, apply_cli_overrides

__all__ = [
    "QianWenChatAuto",
    "get_default_config",
    "load_config",
    "apply_cli_overrides",
]
