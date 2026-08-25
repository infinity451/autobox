# -*- coding: utf-8 -*-
"""验证 Playwright 能否用系统自带的 Edge 渲染页面（不下载额外浏览器）。

用 channel="msedge" 让 Playwright 调用系统 Edge。
若成功说明这条路可行（不需要 playwright install chromium）。
"""
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        # 用系统自带的 Edge（Win10/11 都有）
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        # 访问一个真实网站（用 quotes 练习站，动态加载的）
        page.goto("https://quotes.toscrape.com/js/", timeout=15000)
        # 等页面加载完
        page.wait_for_load_state("networkidle", timeout=15000)
        # 拿到渲染后的 HTML
        html = page.content()
        # 检查有没有动态加载的内容（quotes 是 JS 渲染的）
        has_quote = "quote" in html.lower()
        print(f"拿到 HTML 长度: {len(html)} 字节")
        print(f"是否包含动态加载的 quote 内容: {has_quote}")
        # 试试点选一个元素看看
        quote_count = page.locator(".quote").count()
        print(f"页面上 .quote 元素数量: {quote_count}")
        browser.close()
        print("✅ Playwright + 系统 Edge 验证成功" if has_quote and quote_count > 0 else "❌ 未拿到动态内容")


if __name__ == "__main__":
    main()
