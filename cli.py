
"""
通义千问对话爬虫 - 命令行入口模块
负责命令行参数解析、交互模式和主函数
"""

import json
import argparse

from .chat_manager import QianWenChatAuto
from .config import load_config, apply_cli_overrides


def interactive_mode(chat):
    """交互式对话模式"""
    print("\n" + "=" * 60)
    print("  通义千问对话爬虫 - 交互模式")
    print("  输入消息与通义千问对话，输入以下命令进行操作：")
    print("  /quit   - 退出程序")
    print("  /save   - 保存对话历史")
    print("  /new    - 开始新对话")
    print("  /history - 查看对话历史")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("\n你: ").strip()

            if not user_input:
                continue

            if user_input == "/quit":
                print("[*] 正在退出...")
                break
            elif user_input == "/save":
                print("[*] 网站自动保存对话历史，无需手动保存")
                continue
            elif user_input == "/new":
                chat.new_chat()
                continue
            elif user_input == "/history":
                history = chat.get_chat_history()
                if not history:
                    print("[*] 暂无对话历史")
                else:
                    for item in history:
                        role = "你" if item["role"] == "user" else "千问"
                        print(f"  [{role}]: {item['content'][:100]}")
                continue

            response = chat.send_message(user_input)
            print(f"\n千问: {response}")

        except KeyboardInterrupt:
            print("\n[*] 检测到Ctrl+C，正在退出...")
            break
        except Exception as e:
            print(f"[!] 发生错误: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="通义千问对话爬虫(自动驱动版)")
    parser.add_argument("--url", type=str, default=None, help="通义千问聊天页面URL")
    parser.add_argument("--headless", action="store_true", help="使用无头模式运行浏览器")
    parser.add_argument("--config", type=str, default=None, help="配置文件路径(JSON)")
    parser.add_argument("--message", type=str, default=None, help="直接发送单条消息")
    parser.add_argument("--batch", type=str, default=None, help="批量消息文件路径(每行一条消息)")
    parser.add_argument("--output", type=str, default=None, help="对话历史输出文件名")
    parser.add_argument("--timeout", type=int, default=None, help="等待回复超时时间(秒)")
    parser.add_argument("--user-data-dir", type=str, default=None, help="Chrome用户数据目录(保持登录状态)")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 命令行参数覆盖配置
    overrides = {}
    if args.headless:
        overrides["headless"] = True
    if args.timeout:
        overrides["response_wait_timeout"] = args.timeout
    if args.user_data_dir:
        overrides["user_data_dir"] = args.user_data_dir
    config = apply_cli_overrides(config, **overrides)

    chat = QianWenChatAuto(config)

    try:
        chat.open_chat_page(url=args.url)

        if args.message:
            response = chat.send_message(args.message)
            print(f"\n千问: {response}")
        elif args.batch:
            try:
                with open(args.batch, "r", encoding="utf-8") as f:
                    messages = [line.strip() for line in f if line.strip()]
                responses = chat.batch_chat(messages)
                print(f"\n[✓] 批量对话完成，共 {len(responses)} 条回复")
            except FileNotFoundError:
                print(f"[!] 批量消息文件不存在: {args.batch}")
        else:
            interactive_mode(chat)

    finally:
        chat.close()


if __name__ == "__main__":
    main()
