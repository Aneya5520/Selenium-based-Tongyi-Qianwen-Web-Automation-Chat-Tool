"""
通义千问对话爬虫 - 自动驱动版
使用webdriver-manager自动管理ChromeDriver，无需手动下载

!! 此文件保留用于向后兼容，实际代码已拆分到以下模块：
    - config.py: 配置管理
    - browser.py: 浏览器管理
    - hooks.py: JS Hook与网络拦截
    - page_interactor.py: 页面交互
    - response_parser.py: 响应解析
    - chat_manager.py: 对话管理（核心类）
    - cli.py: 命令行入口
"""

# 从新模块导入，保持向后兼容
from .chat_manager import QianWenChatAuto
from .config import get_default_config, load_config
from .cli import main, interactive_mode

__all__ = [
    "QianWenChatAuto",
    "get_default_config",
    "load_config",
    "main",
    "interactive_mode",
]


# 支持直接运行此文件: python qianwen_chat_auto.py
if __name__ == "__main__":
    main()
