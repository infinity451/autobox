# -*- coding: utf-8 -*-
"""GitHub 灵感搜索工具：按关键词搜索 GitHub 上的开源项目。

用法：python fetch_github.py
输出：每个关键词下 Star 最多的前几个项目（名称、Star 数、简介）
用途：帮我们找“自动化工具箱”相关的开源项目，借鉴架构和功能。

注意：GitHub 未登录 API 每小时限 60 次，本脚本只查 6 组关键词，足够用。
"""

# 导入 requests：发网络请求
import requests

# 要搜索的关键词组：每个元组是（显示名, 搜索词）
# GitHub 搜索语法：q=搜索词，按 Star 数排序，每页取前 6 个
QUERIES = [
    ("文件自动化", "file automation organize rules watch folder python"),
    ("工作流引擎", "automation workflow engine if then rules"),
    ("无代码爬虫", "no-code web scraper visual"),
    ("宏录制器", "macro recorder mouse keyboard automation"),
    ("定时关机", "shutdown timer schedule desktop"),
    ("桌面自动化", "desktop automation trigger action"),
]


def search(query: str, per_page: int = 6) -> list[dict]:
    """调用 GitHub 搜索 API，返回项目列表。"""
    # GitHub 仓库搜索接口；q=关键词 & 按 star 数排序 & 取前 per_page 个
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": per_page}
    # 加个 User-Agent 头（GitHub API 要求必须带，否则拒绝）
    headers = {"User-Agent": "autobox-research"}
    # 发请求，超时 15 秒
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    # 状态码不是 200 就抛异常（比如限流了）
    resp.raise_for_status()
    # 返回 items 列表（每个 item 是一个项目的信息）
    return resp.json().get("items", [])


def main() -> None:
    """遍历所有关键词，打印结果。"""
    # 遍历每一组关键词
    for label, query in QUERIES:
        # 分隔线，方便阅读
        print("=" * 70)
        print(f"【{label}】搜索词: {query}")
        print("=" * 70)
        # 尝试搜索；失败（限流/网络）就打印提示继续下一组
        try:
            # 拿到项目列表
            items = search(query)
            # 没有结果
            if not items:
                print("  (无结果)")
            # 逐个打印：名称、Star 数、简介（截断 100 字）
            for it in items:
                name = it["full_name"]                        # 完整名，如 n8n-io/n8n
                stars = it["stargazers_count"]                # Star 数
                desc = (it.get("description") or "无简介")     # 简介
                desc = desc[:100]                              # 截断，防止太长
                print(f"  ⭐{stars:>6}  {name}")
                print(f"           {desc}")
        except Exception as e:  # noqa: BLE001
            # 打印错误（比如触发限流）
            print(f"  搜索失败: {e}")
        # 每组之间稍微停一下，避免请求太密集
        print()


if __name__ == "__main__":
    main()
