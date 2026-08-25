# -*- coding: utf-8 -*-
"""GitHub 灵感搜索工具：按关键词搜索 GitHub 上的开源项目。

用法：python fetch_github.py
输出：每个关键词下 Star 最多的前几个项目（名称、Star 数、简介）
用途：帮我们找“自动化工具箱”相关的开源项目，借鉴架构和功能。
"""

# 导入 requests：发网络请求
import requests
# 导入 urllib3 并关闭警告：本机 SSL 证书链不被信任（代理/加速器导致），
# 搜公开仓库信息用 verify=False 临时跳过。正式使用建议修复证书信任。
import urllib3

urllib3.disable_warnings()

# 要搜索的关键词组：每个元组是（显示名, 搜索词）
# 覆盖 AutoBox 的几大方向：文件自动化、动态爬虫、宏录制、桌面自动化、工作流、Python 桌面
QUERIES = [
    ("文件自动化", "file organizer automation rules move files organization"),
    ("动态爬虫", "playwright scrap web scraping dynamic"),
    ("宏录制", "macro recorder automation mouse keyboard windows"),
    ("桌面自动化", "desktop automation ifttt rules trigger"),
    ("定时任务", "task scheduler reminder desktop app python"),
    ("自动化工作流", "workflow automation self-hosted zapier alternative"),
    ("Python 桌面应用", "python desktop gui application pywebview"),
]


def search(query: str, per_page: int = 8) -> list[dict]:
    """调用 GitHub 搜索 API，返回项目列表。"""
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    headers = {"User-Agent": "autobox-research"}
    # 发请求，超时 15 秒
    # verify=False：本机证书链不被信任，搜索公开仓库信息临时跳过验证
    resp = requests.get(url, params=params, headers=headers, timeout=15, verify=False)
    resp.raise_for_status()
    return resp.json().get("items", [])


def main() -> None:
    """遍历所有关键词，打印结果。"""
    for label, query in QUERIES:
        print("=" * 70)
        print(f"【{label}】搜索词: {query}")
        print("=" * 70)
        try:
            items = search(query)
            if not items:
                print("  (无结果)")
            for it in items:
                name = it["full_name"]
                stars = it["stargazers_count"]
                desc = (it.get("description") or "无简介")[:90]
                print(f"  ⭐{stars:>6}  {name}")
                print(f"           {desc}")
        except Exception as e:  # noqa: BLE001
            print(f"  搜索失败: {e}")
        print()


if __name__ == "__main__":
    main()
