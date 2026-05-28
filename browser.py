
"""
通义千问对话爬虫 - 浏览器管理模块
负责Chrome浏览器初始化、选项配置和反检测
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False


def create_chrome_options(config):
    """
    根据配置创建Chrome选项

    Args:
        config: 配置字典

    Returns:
        Chrome Options对象
    """
    chrome_options = Options()

    if config.get("headless"):
        chrome_options.add_argument("--headless=new")

    # 基本反检测和稳定性设置
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=zh-CN")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # 用户数据目录（保持登录状态）
    if config.get("user_data_dir"):
        chrome_options.add_argument(f"--user-data-dir={config['user_data_dir']}")

    # 排除自动化标识
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    return chrome_options


def init_browser(config):
    """
    初始化Chrome浏览器

    Args:
        config: 配置字典

    Returns:
        (driver, wait) 元组
    """
    chrome_options = create_chrome_options(config)

    # 自动管理ChromeDriver
    if HAS_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("[✓] 使用webdriver-manager自动安装ChromeDriver")
    else:
        driver = webdriver.Chrome(options=chrome_options)
        print("[✓] 使用系统ChromeDriver")

    # 设置超时
    driver.set_page_load_timeout(config.get("page_load_timeout", 30))
    driver.implicitly_wait(0)  # 设为0，避免find_element隐式等待

    wait = WebDriverWait(driver, config.get("element_wait_timeout", 20))

    # 移除webdriver标识
    remove_webdriver_flag(driver)

    print("[✓] 浏览器初始化完成")
    return driver, wait


def remove_webdriver_flag(driver):
    """
    移除navigator.webdriver标识

    Args:
        driver: Selenium WebDriver实例
    """
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
            """
        },
    )
