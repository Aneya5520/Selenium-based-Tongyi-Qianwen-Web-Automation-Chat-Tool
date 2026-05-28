
"""
通义千问对话爬虫 - JS Hook与网络拦截模块
负责注入JS Hook拦截fetch流式响应，以及轮询读取拦截结果
"""


# JS Hook代码，用于拦截通义千问的fetch流式响应
HOOK_SCRIPT = r"""
(function() {
    // 存储拦截到的AI回复
    window.__qianwen_latest = "";        // 累积的完整回复文本
    window.__qianwen_complete = false;
    window.__qianwen_hook_errors = [];
    window.__qianwen_fetch_calls = [];
    window.__qianwen_accumulated = "";   // 用于增量拼接的累积文本

    // 解析流式数据中的AI回复内容
    function parseStreamChunk(text) {
        var lines = text.split("\n");
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            if (!line) continue;

            // 处理SSE格式: data:JSON
            var jsonStr = null;
            if (line.indexOf("data:") === 0) {
                jsonStr = line.substring(5).trim();
                if (jsonStr === "[DONE]") {
                    window.__qianwen_complete = true;
                    continue;
                }
            }
            // 格式1: message{...} 或 complete{...}
            else if (line.indexOf("message") === 0) {
                jsonStr = line.substring(7).trim();
            } else if (line.indexOf("complete") === 0) {
                jsonStr = line.substring(8).trim();
                window.__qianwen_complete = true;
            }
            // 格式2: 纯JSON行
            else if (line.indexOf("{") === 0) {
                jsonStr = line;
            }
            // 格式3: id:xxx 事件行，跳过
            else {
                continue;
            }

            if (!jsonStr) continue;

            try {
                var data = JSON.parse(jsonStr);

                // 通义千问v2格式: {"error_msg":"","data":{"messages":[...]}}
                if (data.data && data.data.messages) {
                    var msgs = data.data.messages;
                    for (var j = 0; j < msgs.length; j++) {
                        var msg = msgs[j];
                        // 提取文本内容 - 全量覆盖
                        if (msg.content) {
                            window.__qianwen_latest = msg.content;
                            window.__qianwen_accumulated = msg.content;
                        }
                        // 检查完成状态
                        if (msg.status === "complete" || msg.status === "finished") {
                            window.__qianwen_complete = true;
                        }
                    }
                }

                // 直接messages格式
                if (data.messages && !data.data) {
                    var msgs = data.messages;
                    for (var j = 0; j < msgs.length; j++) {
                        if (msgs[j].content) {
                            window.__qianwen_latest = msgs[j].content;
                            window.__qianwen_accumulated = msgs[j].content;
                        }
                        if (msgs[j].status === "complete") {
                            window.__qianwen_complete = true;
                        }
                    }
                }

                // 简单text格式 - 全量覆盖
                if (data.text) {
                    window.__qianwen_latest = data.text;
                    window.__qianwen_accumulated = data.text;
                }
                if (data.done) {
                    window.__qianwen_complete = true;
                }

                // choices格式（OpenAI兼容）- 增量拼接
                if (data.choices && data.choices.length > 0) {
                    var delta = data.choices[0].delta || data.choices[0].message;
                    if (delta && delta.content) {
                        // delta.content 是增量文本，需要拼接
                        window.__qianwen_accumulated += delta.content;
                        window.__qianwen_latest = window.__qianwen_accumulated;
                    } else if (data.choices[0].message && data.choices[0].message.content) {
                        // message.content 是全量文本，直接覆盖
                        window.__qianwen_latest = data.choices[0].message.content;
                        window.__qianwen_accumulated = data.choices[0].message.content;
                    }
                    if (data.choices[0].finish_reason === "stop") {
                        window.__qianwen_complete = true;
                    }
                }

                // 检查error_msg为空且有output字段 - 全量覆盖
                if (data.output) {
                    if (data.output.text) {
                        window.__qianwen_latest = data.output.text;
                        window.__qianwen_accumulated = data.output.text;
                    }
                    if (data.output.finish_reason === "stop") {
                        window.__qianwen_complete = true;
                    }
                }

            } catch(e) {
                // JSON解析失败，可能是流式中间片段
            }
        }
    }

    // Hook fetch - 精确匹配通义千问的chat API
    var origFetch = window.fetch.bind(window);
    window.fetch = function() {
        var url = arguments[0];
        var urlStr = (typeof url === "string") ? url : (url.url || "");

        // 记录所有fetch调用
        window.__qianwen_fetch_calls.push(urlStr.substring(0, 100));

        var result = origFetch.apply(this, arguments);

        // 拦截所有fetch请求的响应，记录并尝试解析
        return result.then(function(response) {
            // 记录所有响应URL
            window.__qianwen_fetch_calls.push("RESP: " + urlStr.substring(0, 120));

            // 对所有qianwen相关请求尝试解析响应
            if (urlStr.indexOf("qianwen") >= 0 || urlStr.indexOf("chat") >= 0
                || urlStr.indexOf("completion") >= 0 || urlStr.indexOf("generate") >= 0
                || urlStr.indexOf("dialog") >= 0 || urlStr.indexOf("stream") >= 0) {
                try {
                    var cloned = response.clone();
                    cloned.text().then(function(text) {
                        // 记录响应前200字符用于调试
                        window.__qianwen_hook_errors.push("DATA[" + urlStr.substring(0, 60) + "]: " + text.substring(0, 200));
                        parseStreamChunk(text);
                    }).catch(function(e) {
                        window.__qianwen_hook_errors.push("clone_read: " + e.message);
                    });
                } catch(e) {
                    window.__qianwen_hook_errors.push("clone: " + e.message);
                }
            }
            return response;
        });
    };

    window.__qianwen_hooked = true;
})();
"""


def enable_ws_interception(driver):
    """
    启用网络拦截，通过注入JS hook捕获通义千问的流式回复

    Args:
        driver: Selenium WebDriver实例

    Returns:
        bool: 是否成功注入
    """
    try:
        # 1. 在新文档加载时自动注入（确保SPA导航后也生效）
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": HOOK_SCRIPT}
        )
        # 2. 立即在当前页面也注入一次
        driver.execute_script(HOOK_SCRIPT)
        print("[✓] 网络拦截Hook已注入")
        return True
    except Exception as e:
        print(f"[!] 网络拦截注入失败: {e}，将使用DOM方式获取回复")
        return False


def inject_hook_to_page(driver):
    """
    在已加载的页面中注入Hook（用于页面导航后重新注入）

    Args:
        driver: Selenium WebDriver实例

    Returns:
        bool: 是否成功注入
    """
    try:
        driver.execute_script(HOOK_SCRIPT)
        hooked = driver.execute_script("return window.__qianwen_hooked || false;")
        if hooked:
            print("[✓] 主页面Hook注入成功")
        return hooked
    except Exception as e:
        print(f"[!] 页面Hook注入异常: {e}")
        return False


def inject_hook_to_iframes(driver):
    """
    遍历所有iframe并注入Hook

    Args:
        driver: Selenium WebDriver实例
    """
    from selenium.webdriver.common.by import By

    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"[*] 发现 {len(iframes)} 个iframe")
        for idx, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                driver.execute_script(HOOK_SCRIPT)
                iframe_hooked = driver.execute_script("return window.__qianwen_hooked || false;")
                print(f"  [✓] iframe[{idx}] Hook: {iframe_hooked}")
                driver.switch_to.default_content()
            except Exception as e:
                print(f"  [!] iframe[{idx}] 注入失败: {e}")
                driver.switch_to.default_content()
    except Exception as e:
        print(f"[!] iframe Hook注入异常: {e}")


def enable_cdp_network_interception(driver):
    """
    使用CDP网络事件监听chat API请求和响应

    Args:
        driver: Selenium WebDriver实例
    """
    try:
        driver.execute_cdp_cmd('Network.enable', {})
        print("[✓] CDP网络监听已启用")
    except Exception as e:
        print(f"[!] CDP网络监听启用失败: {e}")


def poll_ws_messages(driver):
    """
    从JS变量中读取拦截到的AI回复

    Args:
        driver: Selenium WebDriver实例

    Returns:
        dict: 包含 latest(最新文本), complete(是否完成) 的字典，失败返回None
    """
    try:
        result = driver.execute_script(
            """
            return {
                hooked: window.__qianwen_hooked || false,
                latest: window.__qianwen_latest || "",
                complete: window.__qianwen_complete || false,
                fetchHooked: typeof window.fetch === "function" && window.fetch.toString().indexOf("origFetch") >= 0,
                fetchCalls: (window.__qianwen_fetch_calls || []).slice(-5),
                errors: (window.__qianwen_hook_errors || []).slice(-3)
            };
            """
        )
        if result:
            return {
                "latest": result.get("latest", ""),
                "complete": result.get("complete", False),
            }
        return None
    except Exception as e:
        print(f"  [Hook] 读取异常: {e}")
        return None


def reset_ws_state(driver):
    """
    重置JS拦截变量（发送消息前调用）

    Args:
        driver: Selenium WebDriver实例
    """
    try:
        driver.execute_script(
            "window.__qianwen_latest = ''; "
            "window.__qianwen_complete = false; "
            "window.__qianwen_accumulated = '';"
        )
    except Exception:
        pass


def check_cdp_network_responses(driver):
    """
    检查网络请求和DOM结构，帮助调试

    Args:
        driver: Selenium WebDriver实例
    """
    try:
        # 1. 检查Performance API中的所有请求
        all_entries = driver.execute_script("""
            var entries = performance.getEntriesByType('resource');
            var result = [];
            for (var i = Math.max(0, entries.length - 30); i < entries.length; i++) {
                var e = entries[i];
                result.push({
                    name: e.name.substring(0, 120),
                    type: e.initiatorType
                });
            }
            return result;
        """)
        if all_entries:
            print("  [调试] 最近30个网络请求:")
            for entry in all_entries:
                print(f"    [{entry.get('type', '?')}] {entry.get('name', '')}")

        # 2. 检查页面DOM结构 - 找到AI回复区域
        dom_info = driver.execute_script("""
            var result = {};
            var selectors = [
                '[class*="chat"]', '[class*="message"]', '[class*="dialog"]',
                '[class*="conversation"]', '[class*="bubble"]', '[class*="markdown"]',
                '[class*="assistant"]', '[class*="bot"]', '[class*="ai-"]',
                '[class*="response"]', '[class*="reply"]', '[class*="answer"]'
            ];
            for (var i = 0; i < selectors.length; i++) {
                var els = document.querySelectorAll(selectors[i]);
                if (els.length > 0) {
                    var samples = [];
                    for (var j = 0; j < Math.min(3, els.length); j++) {
                        samples.push({
                            tag: els[j].tagName,
                            cls: (els[j].className || '').substring(0, 100),
                            text: (els[j].textContent || '').substring(0, 80).trim()
                        });
                    }
                    result[selectors[i]] = {count: els.length, samples: samples};
                }
            }
            return result;
        """)
        if dom_info:
            print("  [调试] DOM结构分析:")
            for selector, info in dom_info.items():
                count = info.get('count', 0)
                samples = info.get('samples', [])
                print(f"    {selector}: {count}个元素")
                for s in samples:
                    print(f"      <{s.get('tag','?')} class=\"{s.get('cls','')[:60]}\"> {s.get('text','')[:60]}")

    except Exception as e:
        print(f"  [调试] 检查异常: {e}")
