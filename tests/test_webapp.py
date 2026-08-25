# -*- coding: utf-8 -*-
"""测试：页面路由（app/webapp.py）。

这个测试专门防"点进模块显示 Not Found"的 bug 复发：
首页能打开，但 /rules.html 等模块页面因为没注册路由而 404。
用 FastAPI 自带的 TestClient 逐一验证页面能打开。
"""

# 导入 TestClient：FastAPI 官方提供的测试客户端（模拟浏览器发请求）
from fastapi.testclient import TestClient

# 导入应用（app/webapp.py 创建）
from app.webapp import app

# 创建一个测试客户端
client = TestClient(app)

# 所有应该能打开的模块页面
PAGES = ["rules.html", "crawler.html", "batch.html", "timer.html", "macro.html"]


def test_index_ok():
    """首页能打开。"""
    r = client.get("/")
    # 200 = 正常
    assert r.status_code == 200


def test_all_module_pages_ok():
    """所有模块页面能打开（防"Not Found"复发）。"""
    # 逐个请求模块页面
    for p in PAGES:
        r = client.get("/" + p)
        # 每个页面都必须 200，否则这个 bug 就复发了
        assert r.status_code == 200, f"页面 {p} 返回 {r.status_code}"


def test_unknown_page_404():
    """不在白名单里的页面返回 404（安全：不暴露任意文件）。"""
    r = client.get("/hack.html")
    assert r.status_code == 404


def test_api_still_works():
    """API 接口没有被页面路由的改动影响。"""
    r = client.get("/api/status")
    # API 正常返回 JSON
    assert r.status_code == 200
    assert "version" in r.json()
