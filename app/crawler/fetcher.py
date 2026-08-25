# -*- coding: utf-8 -*-
"""抓取解析引擎：把网页抓下来，再按 CSS 选择器提取数据。

两个核心函数：
- fetch_html(url)：发网络请求拿网页源码（带伪装浏览器头）
- parse_items(html, ...)：用 BeautifulSoup 解析，按选择器提取成记录列表

什么是 CSS 选择器（简单理解）：
- div.news-item     = 找 class 是 news-item 的 div 标签
- h2                = 找所有 h2 标题
- a                 = 找所有 a 链接
- .date             = 找 class 是 date 的元素
- #title            = 找 id 是 title 的元素
网页结构 = 一层套一层的标签，选择器就是“怎么定位到目标元素”的路径。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 requests：发网络请求（抓网页）
import requests
# 导入 BeautifulSoup：HTML 解析库，能把网页源码变成“可以按选择器查找”的结构
from bs4 import BeautifulSoup

# 默认请求头：伪装成浏览器访问，很多网站会拒绝“默认爬虫头”
# 简单理解：不带这个头，服务器可能认出“你不是浏览器”，拒绝给你网页
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",  # 告诉服务器我们要中文网页
}


def fetch_html(url: str, timeout: int = 15, dynamic: bool = False, wait_selector: str = "") -> str:
    """抓取网页源码。

    参数：
        url: 网页地址
        timeout: 超时秒数（网络不好时防止卡死）
        dynamic: 是否为动态网页（内容靠 JavaScript 加载）
        wait_selector: 等待选择器（动态页等到该元素出现再抓取；空则不等待特定元素）
    返回：
        网页源码字符串（HTML）
    异常：
        网络错误 / HTTP 错误码（404 等）会抛异常，由调用方处理
    """
    # 动态网页：用浏览器渲染（Playwright + 系统 Edge），拿到 JS 执行后的完整 HTML
    if dynamic:
        return fetch_html_render(url, timeout, wait_selector)
    # 静态网页：直接发请求拿 HTML（快、轻）
    return fetch_html_requests(url, timeout)


def fetch_html_requests(url: str, timeout: int = 15) -> str:
    """静态网页抓取（原方案）：requests 直接拿 HTML 源码。"""
    # 发 GET 请求；headers 伪装浏览器，timeout 防卡死
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    # raise_for_status()：状态码不是 200 就抛异常（比如 404 页面不存在）
    resp.raise_for_status()
    # 网页编码处理：优先用服务器声明的编码，识别不出就用“猜”
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    # 返回网页文本
    return resp.text


def fetch_html_render(url: str, timeout: int = 15, wait_selector: str = "") -> str:
    """动态网页抓取：用浏览器渲染，拿到 JS 执行后的完整 HTML。

    原理：很多现代网页的内容是 JavaScript 动态生成的，直接 requests 拿到的是
    空壳。这里用 Playwright 打开真实浏览器（用 Windows 自带的 Edge）渲染页面，
    等动态内容加载完，再取渲染后的 HTML —— 剩下的解析逻辑和静态页完全一样。

    参数：
        url: 网页地址
        timeout: 超时秒数
        wait_selector: 等待选择器（推荐配置：等目标内容出现，比如 "div.news-item"）。
             动态加载的内容往往几秒后才出现，等它出现再抓最稳。
             留空则等"网络空闲"（networkidle，也常能覆盖动态加载）。
    """
    # 延迟导入：只有真正用到动态爬虫时才加载（避免普通请求也带上这个重依赖）
    from playwright.sync_api import sync_playwright

    # 用 with 管理 Playwright 生命周期（自动启动/关闭）
    with sync_playwright() as p:
        # channel="msedge"：用系统自带 Edge，不用额外下载 Chromium
        # headless=True：无头模式（不弹出浏览器窗口，后台渲染）
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            # 打开一个空白页面
            page = browser.new_page()
            # 访问目标网页（timeout 转成毫秒）
            page.goto(url, timeout=timeout * 1000)
            # 动态内容"等它出现"：
            if wait_selector:
                # 等到指定元素出现在页面上（这正是动态加载完成的信号）
                page.wait_for_selector(wait_selector, timeout=timeout * 1000)
            else:
                # 没配置选择器：等网络空闲（页面不再请求新资源，通常也加载完了）
                page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            # 拿到渲染后的完整 HTML
            return page.content()
        finally:
            # 无论成功失败都关闭浏览器（释放资源）
            browser.close()


def extract_value(node, attr: str) -> str:
    """从一个 HTML 元素里取出要的值。

    参数：
        node: BeautifulSoup 的元素对象（可能为 None = 元素不存在）
        attr: 取值方式：
            "text"        → 元素的文本内容（如“标题文字”）
            "html"        → 元素的 HTML 源码
            "attr.href"   → 元素的 href 属性（链接）
            "attr.src"    → 元素的 src 属性（图片地址）
    返回：
        提取到的字符串；元素不存在时返回空字符串
    """
    # 元素不存在（选择器没匹配到）：返回空字符串，不报错
    if node is None:
        return ""
    # 取文本：get_text(strip=True) 拿元素里的所有文字并去掉首尾空格
    if attr == "text":
        return node.get_text(strip=True)
    # 取 HTML 源码
    if attr == "html":
        return str(node)
    # 取属性：attr.xxx 形式，比如 attr.href 取 href 属性
    if attr.startswith("attr."):
        # 属性名是 attr 后面的部分
        prop = attr[5:]
        # node.get(prop, "")：取属性值，没有就返回空字符串
        return node.get(prop, "")
    # 未知取值方式：返回空
    return ""


def parse_items(html: str, item_selector: str, fields: list, max_items: int) -> list[dict]:
    """解析网页，按配置提取记录列表。

    参数：
        html: 网页源码
        item_selector: 列表容器选择器（每条记录的外壳）
        fields: 字段配置列表，如 [{"name": "标题", "selector": "h2", "attr": "text"}]
        max_items: 最多提取多少条
    返回：
        记录列表，如 [{"标题": "新闻1", "链接": "https://..."}, ...]
    """
    # 用 lxml 解析器把 HTML 变成可查询的结构（lxml 比默认解析器快且容错好）
    soup = BeautifulSoup(html, "lxml")
    # soup.select(选择器)：按选择器找到所有匹配的元素
    # 这里找“列表容器”，每个容器代表一条记录
    containers = soup.select(item_selector)

    # 最终结果列表
    records = []
    # 只取前 max_items 条（防止页面太大）
    for el in containers[:max_items]:
        # 单条记录字典
        row = {}
        # 逐个字段提取
        for f in fields:
            # 在“这一条记录的容器”里查找字段选择器匹配的元素
            # 注意是 el.select_one()（在当前容器内部找），不是 soup.select_one()（全页面找）
            node = el.select_one(f["selector"]) if f["selector"] else el
            # 提取值，存进记录（字段名 → 值）
            row[f["name"]] = extract_value(node, f.get("attr", "text"))
        # 把这条记录加进结果
        records.append(row)
    # 返回所有记录
    return records
