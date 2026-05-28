
"""
通义千问对话爬虫 - 对话管理模块
核心业务逻辑，组合浏览器、Hook、页面交互和响应解析模块
"""

import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from . import browser
from . import hooks
from . import page_interactor
from . import response_parser
from .config import get_default_config, load_config


class QianWenChatAuto:
    """通义千问对话爬虫类 - 自动驱动版"""

    BASE_URL = "https://www.qianwen.com/chat"

    def __init__(self, config=None):
        """
        初始化通义千问对话爬虫

        Args:
            config: 配置字典
        """
        self.config = config or get_default_config()
        self.driver = None
        self.wait = None
        self.chat_history = []
        # WebSocket拦截相关
        self._ws_listening = False

    def open_chat_page(self, url=None):
        """打开通义千问聊天页面"""
        if self.driver is None:
            self.driver, self.wait = browser.init_browser(self.config)
            # 启用WebSocket拦截
            self._ws_listening = hooks.enable_ws_interception(self.driver)

        target_url = url or self.BASE_URL
        print(f"[*] 正在打开通义千问页面: {target_url}")
        self.driver.get(target_url)
        time.sleep(3)

        # 页面加载后重新注入Hook（新页面会清除JS环境）
        if self._ws_listening:
            try:
                # 在主页面注入Hook
                hooks.inject_hook_to_page(self.driver)

                # 遍历所有iframe并注入Hook
                hooks.inject_hook_to_iframes(self.driver)

                # 启用CDP网络拦截作为备用方案
                hooks.enable_cdp_network_interception(self.driver)

            except Exception as e:
                print(f"[!] 页面Hook注入异常: {e}")
                self._ws_listening = False

        print("[*] 页面已加载，请确保已登录通义千问账号")
        print("[*] 如果需要登录，请在浏览器中手动完成登录操作")
        page_interactor.wait_for_login(self.driver)
        print("[✓] 页面准备就绪")

    def send_message(self, message, wait_response=True):
        """
        发送消息给通义千问

        Args:
            message: 要发送的消息内容
            wait_response: 是否等待回复

        Returns:
            通义千问的回复内容
        """
        if self.driver is None:
            raise RuntimeError("浏览器未初始化，请先调用 open_chat_page()")

        page_interactor.send_message(self.driver, message, ws_listening=self._ws_listening)

        if wait_response:
            response = response_parser.wait_for_response(
                self.driver, self.config, ws_listening=self._ws_listening
            )
            if response:
                # print(f"[✓] 收到回复: {response[:80]}{'...' if len(response) > 80 else ''}")
                #
                print(response)
            else:
                print("[!] 收到空回复")
            return response

        return None

    def get_chat_history(self):
        """获取对话历史"""
        return self.chat_history

    def save_chat_history(self, filename=None):
        """保存对话历史到JSON文件（已禁用，网站自动保存）"""
        pass

    def batch_chat(self, messages, interval=3):
        """
        批量发送消息

        Args:
            messages: 消息列表
            interval: 每条消息之间的间隔时间(秒)

        Returns:
            回复列表
        """
        responses = []
        for i, msg in enumerate(messages):
            print(f"[=== 第 {i+1}/{len(messages)} 条消息 ===]")
            try:
                response = self.send_message(msg)
                responses.append(response)
            except Exception as e:
                print(f"[!] 第 {i+1} 条消息发送失败: {e}")
                responses.append(None)

            if i < len(messages) - 1:
                time.sleep(interval)

        return responses

    def new_chat(self):
        """开始新对话"""
        try:
            selectors = [
                (By.CSS_SELECTOR, "button[class*='new']"),
                (By.XPATH, "//button[contains(text(), '新建')]"),
                (By.XPATH, "//button[contains(text(), '新对话')]"),
                (By.CSS_SELECTOR, "[class*='new-chat']"),
            ]

            for by, selector in selectors:
                try:
                    element = self.driver.find_element(by, selector)
                    if element.is_displayed():
                        element.click()
                        time.sleep(2)
                        print("[✓] 已创建新对话")
                        return
                except NoSuchElementException:
                    continue

            print("[*] 未找到新建对话按钮，刷新页面")
            self.driver.refresh()
            time.sleep(3)
            page_interactor.wait_for_login(self.driver)

        except Exception as e:
            print(f"[!] 创建新对话失败: {e}")

    def close(self):
        """关闭浏览器并保存对话历史"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("[✓] 浏览器已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
