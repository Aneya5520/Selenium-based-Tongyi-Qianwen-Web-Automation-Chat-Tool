# QianWen Chat Crawler 🤖

<p align="center">
  <strong>基于 Selenium 的通义千问网页版自动化对话工具</strong>
</p>

<p align="center">
  <a href="#安装">安装</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#使用方式">使用方式</a> •
  <a href="#项目结构">项目结构</a> •
  <a href="#配置说明">配置说明</a> •
  <a href="#api-参考">API 参考</a>
</p>

---

## ✨ 功能特性

- 🤖 自动化与通义千问网页版对话交互
- 💬 交互式终端对话模式
- 📨 单条消息快速发送
- 📦 批量消息文件导入
- 🔗 Fetch Hook 拦截流式响应，精准捕获 AI 回复
- 🔍 多策略 DOM 降级解析（Markdown → 对话容器 → 语义类名 → 暴力搜索）
- 🔒 Chrome 用户数据目录保持登录状态
- 🛡️ 反自动化检测（移除 webdriver 标识）
- 🧩 模块化架构，职责清晰，易于扩展和维护

## 安装

### 前置条件

- Python 3.8+
- Google Chrome 浏览器

### 安装依赖

```bash
pip install -r requirements.txt
```

> `webdriver-manager` 会自动管理 ChromeDriver，无需手动下载。

## 快速开始

```bash
# 交互式对话（推荐首次使用）
python -m paqu

# 单条消息
python -m paqu --message "你好，请介绍一下自己"

# 批量对话
python -m paqu --batch messages.txt
```

首次运行会自动打开浏览器，请手动登录通义千问账号，登录成功后即可在终端中对话。

## 使用方式

### 1. 交互式对话模式

```bash
python -m paqu
```

```
你: 你好，请介绍一下自己
千问: 你好！我是通义千问...

你: /save        # 保存对话历史
你: /new         # 开始新对话
你: /history     # 查看对话历史
你: /quit        # 退出程序
```

### 2. 单条消息模式

```bash
python -m paqu --message "你好，请介绍一下应急响应的流程"
```

### 3. 批量消息模式

创建消息文件 `messages.txt`，每行一条消息：

```text
什么是应急响应？
应急响应的主要步骤有哪些？
如何进行应急响应的复盘？
```

运行：

```bash
python -m paqu --batch messages.txt
```

### 4. 使用自定义配置

```bash
python -m paqu --config config.json
```

### 5. 保持登录状态

设置 Chrome 用户数据目录，避免每次都需要登录：

```bash
python -m paqu --user-data-dir "C:\chrome_data\qianwen"
```

### 6. 无头模式

```bash
python -m paqu --headless --message "你好"
```

### 7. 指定超时时间

```bash
python -m paqu --timeout 180
```

## 命令行参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `--url` | str | 通义千问聊天页面 URL |
| `--headless` | flag | 使用无头模式运行浏览器 |
| `--config` | str | 配置文件路径（JSON） |
| `--message` | str | 直接发送单条消息 |
| `--batch` | str | 批量消息文件路径（每行一条） |
| `--output` | str | 对话历史输出文件名 |
| `--timeout` | int | 等待回复超时时间（秒） |
| `--user-data-dir` | str | Chrome 用户数据目录 |

## 项目结构

```
paqu/
├── __init__.py           # 包入口，导出核心类和函数
├── __main__.py           # 支持 python -m paqu 运行
├── config.py             # 配置管理（默认配置、加载配置、CLI 覆盖）
├── browser.py            # 浏览器管理（Chrome 初始化、选项配置、反检测）
├── hooks.py              # JS Hook 脚本与网络拦截（Fetch 拦截、WS 轮询）
├── page_interactor.py    # 页面交互（查找输入框/按钮、发送消息、等待登录）
├── response_parser.py    # 响应解析（WS 拦截优先 → DOM 多策略降级）
├── chat_manager.py       # 对话管理（核心类 QianWenChatAuto）
├── cli.py                # 命令行入口（参数解析、交互模式、主函数）
├── qianwen_chat_auto.py  # 向后兼容导入包装
├── config.json           # 默认配置文件
└── requirements.txt      # Python 依赖
```

### 模块依赖关系

```
cli.py
  └── chat_manager.py (QianWenChatAuto)
        ├── config.py        → 配置管理
        ├── browser.py       → 浏览器初始化
        ├── hooks.py         → 网络拦截
        ├── page_interactor.py → 页面交互
        │     └── hooks.py
        └── response_parser.py → 响应解析
              └── hooks.py
```

## 配置说明

`config.json` 配置项：

```json
{
    "headless": false,
    "page_load_timeout": 30,
    "element_wait_timeout": 20,
    "typing_interval": 0.03,
    "response_wait_timeout": 120,
    "save_history": false,
    "history_dir": "chat_history",
    "user_data_dir": null
}
```

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `headless` | bool | `false` | 是否使用无头模式 |
| `page_load_timeout` | int | `30` | 页面加载超时（秒） |
| `element_wait_timeout` | int | `20` | 元素等待超时（秒） |
| `typing_interval` | float | `0.03` | 模拟打字间隔（秒） |
| `response_wait_timeout` | int | `120` | 等待 AI 回复超时（秒） |
| `save_history` | bool | `false` | 是否保存对话历史（网站自动保存） |
| `history_dir` | str | `"chat_history"` | 对话历史保存目录 |
| `user_data_dir` | str | `null` | Chrome 用户数据目录 |

## API 参考

### 基本用法

```python
from paqu import QianWenChatAuto

# 使用默认配置
chat = QianWenChatAuto()

# 使用自定义配置
from paqu import load_config
config = load_config("config.json")
chat = QianWenChatAuto(config)

try:
    # 打开页面（首次需手动登录）
    chat.open_chat_page()

    # 发送单条消息
    response = chat.send_message("你好，请介绍一下应急响应的流程")
    print(f"回复: {response}")

    # 批量对话
    responses = chat.batch_chat([
        "什么是应急响应？",
        "应急响应的主要步骤有哪些？",
    ])

    # 新建对话
    chat.new_chat()

finally:
    chat.close()
```

### 上下文管理器

```python
from paqu import QianWenChatAuto

with QianWenChatAuto() as chat:
    chat.open_chat_page()
    response = chat.send_message("你好")
    print(response)
```

### QianWenChatAuto

| 方法 | 说明 |
|------|------|
| `__init__(config=None)` | 初始化，可传入配置字典 |
| `open_chat_page(url=None)` | 打开通义千问页面 |
| `send_message(message, wait_response=True)` | 发送消息并获取回复 |
| `batch_chat(messages, interval=3)` | 批量发送消息 |
| `new_chat()` | 新建对话 |
| `get_chat_history()` | 获取对话历史 |
| `close()` | 关闭浏览器 |

## 响应获取策略

工具采用**多级降级策略**获取 AI 回复，确保可靠性：

```
1. Fetch Hook 拦截（优先）
   └── 注入 JS Hook 拦截 fetch 请求，解析 SSE 流式响应
   └── 支持多种数据格式：千问v2、OpenAI兼容、纯文本、output格式

2. DOM 解析（降级）
   ├── 策略1: 查找 markdown-body 元素
   ├── 策略2: 查找对话容器内最后一条消息
   ├── 策略3: 查找 assistant/answer/reply 语义类名
   └── 策略4: 暴力搜索最长文本块（排除侧边栏/导航）
```

## 注意事项

1. 首次运行需要**手动登录**通义千问账号
2. 建议使用 `--user-data-dir` 参数保持登录状态，避免重复登录
3. 网页结构可能随通义千问更新而变化，如遇问题可能需要更新选择器
4. 本工具仅供**学习和研究**使用，请遵守通义千问的服务条款

## ⚠️ 免责声明

本项目仅供学习和研究目的。使用本工具时，请确保遵守以下要求：

- 遵守 [通义千问服务协议](https://www.qianwen.com/terms) 及相关法律法规
- 不得用于大规模数据爬取、商业牟利或其他违规用途
- 因使用本工具产生的任何法律责任，由使用者自行承担

## License

[MIT License](LICENSE)
