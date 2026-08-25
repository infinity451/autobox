# -*- coding: utf-8 -*-
"""测试：网页解析与取值（app/crawler/fetcher.py 的 parse_items / extract_value）。"""

# 导入被测函数
from app.crawler.fetcher import extract_value, parse_items, fetch_html_requests

# 模拟一段 HTML（静态页面内容，直接写在 HTML 里）
SAMPLE_HTML = """
<div class="news-item"><h2>新闻1</h2><a href="/a1">链接1</a><span class="date">2026-08-01</span></div>
<div class="news-item"><h2>新闻2</h2><a href="/a2">链接2</a><span class="date">2026-08-02</span></div>
<div class="news-item"><h2>新闻3</h2><a href="/a3">链接3</a><span class="date">2026-08-03</span></div>
"""


def test_parse_items_multiple():
    """能按选择器解析出多条记录。"""
    # 字段配置：标题(h2 文本)、链接(a 的 href)、日期(.date 文本)
    fields = [
        {"name": "标题", "selector": "h2", "attr": "text"},
        {"name": "链接", "selector": "a", "attr": "attr.href"},
        {"name": "日期", "selector": ".date", "attr": "text"},
    ]
    records = parse_items(SAMPLE_HTML, "div.news-item", fields, max_items=10)
    assert len(records) == 3
    assert records[0]["标题"] == "新闻1"
    assert records[0]["链接"] == "/a1"
    assert records[1]["标题"] == "新闻2"


def test_parse_items_max_items():
    """超过 max_items 时只取前 N 条。"""
    fields = [{"name": "标题", "selector": "h2", "attr": "text"}]
    records = parse_items(SAMPLE_HTML, "div.news-item", fields, max_items=2)
    assert len(records) == 2


def test_parse_items_empty_selector():
    """选择器匹配不到 = 空结果（不报错）。"""
    fields = [{"name": "标题", "selector": "h2", "attr": "text"}]
    records = parse_items("<html>没有内容</html>", "div.不存在", fields, max_items=10)
    assert records == []


def test_extract_value_text():
    """取文本。"""
    from bs4 import BeautifulSoup

    node = BeautifulSoup("<h2>你好</h2>", "lxml").find("h2")
    assert extract_value(node, "text") == "你好"


def test_extract_value_attr():
    """取属性。"""
    from bs4 import BeautifulSoup

    node = BeautifulSoup('<a href="/x">链接</a>', "lxml").find("a")
    assert extract_value(node, "attr.href") == "/x"


def test_extract_value_none():
    """节点不存在时返回空字符串（不报错）。"""
    assert extract_value(None, "text") == ""


def test_fetch_html_requests_raises_on_bad_url():
    """status 404 的地址会抛异常（网络错误由调用方处理）。"""
    import pytest

    # 一个不存在的本地地址 → requests 抛 HTTPError
    with pytest.raises(Exception):
        fetch_html_requests("http://127.0.0.1:8000/不存在页面12345", timeout=5)
