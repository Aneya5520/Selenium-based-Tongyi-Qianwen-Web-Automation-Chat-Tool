
"""
通义千问对话爬虫 - 响应解析模块
负责从DOM中解析AI回复内容（多种策略）
"""

import time
from selenium.common.exceptions import TimeoutException

from . import hooks


def wait_for_response(driver, config, ws_listening=False):
    """
    等待通义千问的回复（优先WebSocket拦截，降级DOM解析）

    Args:
        driver: Selenium WebDriver实例
        config: 配置字典
        ws_listening: 是否已启用WebSocket拦截

    Returns:
        str: AI回复内容

    Raises:
        TimeoutException: 等待回复超时
    """
    print("[*] 等待通义千问回复...")

    timeout = config.get("response_wait_timeout", 120)
    start_time = time.time()

    # 方式1: WebSocket拦截（快速精准）
    if ws_listening:
        print("[*] 使用WebSocket拦截模式等待回复...")
        ws_text = ""
        ws_complete = False

        while time.time() - start_time < timeout:
            result = hooks.poll_ws_messages(driver)
            if result:
                if result["latest"]:
                    ws_text = result["latest"]
                if result["complete"] and ws_text:
                    print("[✓] WebSocket拦截获取回复完成")
                    return ws_text

                # 如果已有部分内容，打印进度
                if ws_text and int(time.time() - start_time) % 3 == 0:
                    print(f"[*] 正在接收回复: {ws_text[:50]}...")

            time.sleep(0.1)  # 高频轮询，WebSocket消息来得很快

        # 超时但有部分内容
        if ws_text:
            print("[!] WebSocket等待超时，返回已获取的部分回复")
            return ws_text

        # 检查CDP网络请求，帮助调试
        print("[*] Hook未捕获chat请求，检查网络请求...")
        hooks.check_cdp_network_responses(driver)

    # 方式2: DOM解析降级方案
    print("[*] WebSocket未捕获回复，降级使用DOM解析...")
    last_response = ""
    stable_count = 0
    min_wait = 5  # 最少等待5秒，避免短暂停顿误判为完成

    while time.time() - start_time < timeout:
        time.sleep(0.5)
        elapsed = time.time() - start_time
        current_response = get_latest_response(driver)

        if current_response:
            if current_response == last_response and len(current_response) > 0:
                stable_count += 1
                # 必须同时满足：已过最小等待时间 + 内容持续稳定
                if stable_count >= 6 and elapsed > min_wait:
                    print("[✓] 回复已完成（DOM内容稳定）")
                    return current_response
            else:
                stable_count = 0
                last_response = current_response

    if last_response:
        print("[!] 等待回复超时，返回已获取的部分回复")
        return last_response

    raise TimeoutException("等待通义千问回复超时")


def get_latest_response(driver):
    """
    获取通义千问的最新回复内容（使用多策略DOM解析）

    Args:
        driver: Selenium WebDriver实例

    Returns:
        str: AI回复内容，未找到返回空字符串
    """
    result = driver.execute_script(
        '''
        // 策略1: 找markdown-body元素（AI回复最可能的渲染容器）
        var mdSelectors = [
            '[class*="markdown-body"]', '[class*="markdownContent"]',
            '[class*="md-body"]', '[class*="markdown"]', '[class*="mdBody"]',
            '[class*="rich-text"]', '[class*="richText"]', '[class*="html-body"]'
        ];
        for (var s = 0; s < mdSelectors.length; s++) {
            var els = document.querySelectorAll(mdSelectors[s]);
            if (els.length > 0) {
                // 取最后一个（最新的回复）
                var last = els[els.length - 1];
                // 确保不在侧边栏内
                var parent = last.parentElement;
                var inSidebar = false;
                while (parent && parent !== document.body) {
                    var cls = (parent.className || '').toLowerCase();
                    if (cls.indexOf('sidebar') >= 0 || cls.indexOf('nav') >= 0
                        || cls.indexOf('menu') >= 0 || cls.indexOf('side') >= 0) {
                        inSidebar = true;
                        break;
                    }
                    parent = parent.parentElement;
                }
                if (!inSidebar) {
                    var text = (last.innerText || '').trim();
                    if (text.length > 5) return text;
                }
            }
        }

        // 策略2: 找对话容器内的最后一条消息
        var chatContainer = document.querySelector('[class*="chat"][class*="list"]')
            || document.querySelector('[class*="conversation"]')
            || document.querySelector('[class*="dialog"]')
            || document.querySelector('[class*="message-list"]')
            || document.querySelector('[class*="chatContent"]')
            || document.querySelector('[class*="chat-content"]')
            || document.querySelector('[class*="chatBox"]')
            || document.querySelector('[class*="chat-box"]');

        if (chatContainer) {
            var msgBlocks = chatContainer.querySelectorAll(
                '[class*="message"], [class*="msg-item"], [class*="chat-item"], [class*="bubble"]'
            );
            if (msgBlocks.length > 0) {
                var last = msgBlocks[msgBlocks.length - 1];
                var md = last.querySelector('[class*="markdown"]')
                    || last.querySelector('[class*="md-body"]')
                    || last.querySelector('[class*="content"]');
                var target = md || last;
                var text = (target.innerText || '').trim();
                if (text.length > 5) return text;
            }
        }

        // 策略3: 找所有assistant/answer/reply类名
        var allMessages = document.querySelectorAll(
            '[class*="chatItem"], [class*="chat-item"], [class*="messageItem"], [class*="message-item"], '
            + '[class*="assistant"], [class*="answer"], [class*="reply"]'
        );
        if (allMessages.length > 0) {
            for (var i = allMessages.length - 1; i >= 0; i--) {
                var msg = allMessages[i];
                var cls = (msg.className || '').toLowerCase();
                if (cls.indexOf('assistant') >= 0 || cls.indexOf('bot') >= 0
                    || cls.indexOf('ai') >= 0 || cls.indexOf('model') >= 0
                    || cls.indexOf('answer') >= 0 || cls.indexOf('reply') >= 0) {
                    var text = (msg.innerText || '').trim();
                    if (text.length > 5) return text;
                }
            }
            var lastMsg = allMessages[allMessages.length - 1];
            var text = (lastMsg.innerText || '').trim();
            if (text.length > 5) return text;
        }

        // 策略4: 暴力搜索 - 找页面上最长的文本块
        var allDivs = document.querySelectorAll('div');
        var best = '';
        var bestCls = '';
        for (var i = 0; i < allDivs.length; i++) {
            var d = allDivs[i];
            var text = (d.innerText || '').trim();
            // 排除侧边栏和导航
            var parent = d.parentElement;
            var skip = false;
            while (parent && parent !== document.body) {
                var pcls = (parent.className || '').toLowerCase();
                if (pcls.indexOf('sidebar') >= 0 || pcls.indexOf('nav') >= 0
                    || pcls.indexOf('menu') >= 0 || pcls.indexOf('side') >= 0
                    || pcls.indexOf('header') >= 0 || pcls.indexOf('footer') >= 0) {
                    skip = true;
                    break;
                }
                parent = parent.parentElement;
            }
            if (skip) continue;
            // 找含有较长文本但子div不多的元素（叶节点优先）
            var childDivs = d.querySelectorAll('div');
            if (text.length > 20 && text.length < 10000 && childDivs.length <= 5) {
                if (text.length > best.length) {
                    best = text;
                    bestCls = (d.className || '').substring(0, 80);
                }
            }
        }
        if (best) return best;

        return '';
        '''
    )
    if result:
        return result

    return ""
