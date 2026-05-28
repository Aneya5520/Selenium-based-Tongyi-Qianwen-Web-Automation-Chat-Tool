
"""
通义千问对话爬虫 - 页面交互模块
负责查找页面元素（输入框、发送按钮等）和发送消息
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

from . import hooks


def find_input_box(driver):
    """
    查找聊天输入框（使用JS快速定位）

    Args:
        driver: Selenium WebDriver实例

    Returns:
        输入框WebElement，未找到返回None
    """
    # 先用JS查找所有可能的输入元素
    debug_info = driver.execute_script(
        '''
        var result = {found: null, candidates: []};

        // 查找所有可能的输入元素
        var textareas = document.querySelectorAll('textarea');
        var contentEditables = document.querySelectorAll('[contenteditable="true"]');
        var inputs = document.querySelectorAll('input[type="text"]');
        var roleTextboxes = document.querySelectorAll('[role="textbox"]');

        // 收集信息
        function collectInfo(els, type) {
            for (var i = 0; i < els.length; i++) {
                var e = els[i];
                result.candidates.push({
                    type: type,
                    tag: e.tagName,
                    cls: (e.className || '').substring(0, 80),
                    placeholder: e.getAttribute('placeholder') || '',
                    visible: e.offsetParent !== null,
                    rect: e.getBoundingClientRect().width + 'x' + e.getBoundingClientRect().height
                });
            }
        }

        collectInfo(textareas, 'textarea');
        collectInfo(contentEditables, 'contenteditable');
        collectInfo(inputs, 'input');
        collectInfo(roleTextboxes, 'role-textbox');

        // 优先返回可见的textarea
        for (var i = 0; i < textareas.length; i++) {
            if (textareas[i].offsetParent !== null) {
                result.found = textareas[i];
                return result;
            }
        }
        // 其次返回可见的contenteditable
        for (var i = 0; i < contentEditables.length; i++) {
            if (contentEditables[i].offsetParent !== null) {
                result.found = contentEditables[i];
                return result;
            }
        }
        // 再试role=textbox
        for (var i = 0; i < roleTextboxes.length; i++) {
            if (roleTextboxes[i].offsetParent !== null) {
                result.found = roleTextboxes[i];
                return result;
            }
        }

        return result;
        '''
    )

    if debug_info:
        element = debug_info.get('found')
        if element:
            return element

    # JS找不到再用选择器遍历
    selectors = [
        (By.CSS_SELECTOR, "textarea"),
        (By.CSS_SELECTOR, "[contenteditable='true']"),
        (By.CSS_SELECTOR, "[role='textbox']"),
        (By.CSS_SELECTOR, "input[type='text']"),
        (By.CSS_SELECTOR, "textarea[class*='input']"),
        (By.CSS_SELECTOR, "div[class*='input'] textarea"),
    ]

    for by, selector in selectors:
        try:
            element = driver.find_element(by, selector)
            if element.is_displayed():
                return element
        except NoSuchElementException:
            continue

    return None


def find_send_button(driver):
    """
    查找发送按钮（使用JS快速定位）

    Args:
        driver: Selenium WebDriver实例

    Returns:
        发送按钮WebElement，未找到返回None
    """
    # 优先用JS一次性查找
    element = driver.execute_script(
        '''
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var b = btns[i];
            var cls = b.className || '';
            var text = b.textContent || '';
            var label = b.getAttribute('aria-label') || '';
            if (cls.indexOf('send') >= 0 || cls.indexOf('submit') >= 0
                || text.indexOf('发送') >= 0 || label.indexOf('发送') >= 0
                || label.indexOf('Send') >= 0) {
                return b;
            }
        }
        return null;
        '''
    )
    if element:
        return element

    # 备用选择器
    selectors = [
        (By.CSS_SELECTOR, "button[class*='send']"),
        (By.CSS_SELECTOR, "button[class*='submit']"),
    ]

    for by, selector in selectors:
        try:
            element = driver.find_element(by, selector)
            if element.is_displayed():
                return element
        except NoSuchElementException:
            continue
    return None


def send_message(driver, message, ws_listening=False):
    """
    发送消息给通义千问

    Args:
        driver: Selenium WebDriver实例
        message: 要发送的消息内容
        ws_listening: 是否已启用WebSocket拦截

    Returns:
        bool: 是否成功发送
    """
    print(f"[*] 发送消息: {message[:50]}{'...' if len(message) > 50 else ''}")

    input_box = find_input_box(driver)
    if input_box is None:
        raise NoSuchElementException("未找到聊天输入框，请检查页面是否正确加载")

    input_box.clear()
    time.sleep(0.05)

    # 统一使用send_keys输入（最可靠，模拟真实键盘输入）
    input_box.click()  # 先点击聚焦
    time.sleep(0.1)
    input_box.send_keys(message)

    time.sleep(0.1)

    # 发送前重置JS拦截变量
    if ws_listening:
        hooks.reset_ws_state(driver)

    # 尝试发送
    sent = False
    send_btn = find_send_button(driver)
    if send_btn:
        send_btn.click()
        sent = True
        print("[*] 通过点击发送按钮发送消息")

    if not sent:
        input_box.send_keys(Keys.RETURN)
        sent = True
        print("[*] 通过Enter键发送消息")

    if not sent:
        raise RuntimeError("无法发送消息，未找到发送方式")

    return True


def wait_for_login(driver, timeout=120):
    """
    等待用户登录

    Args:
        driver: Selenium WebDriver实例
        timeout: 超时时间（秒）

    Returns:
        bool: 是否登录成功

    Raises:
        TimeoutException: 登录超时
    """
    from selenium.common.exceptions import TimeoutException

    print(f"[*] 等待登录... (超时: {timeout}秒)")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            input_box = find_input_box(driver)
            if input_box is not None:
                return True
        except Exception:
            pass
        time.sleep(2)

    raise TimeoutException("等待登录超时，请检查是否已成功登录")
