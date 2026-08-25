# -*- coding: utf-8 -*-
"""查询已知知名开源项目的详细信息（按仓库名精确查询）。

用法：python fetch_repos.py
这些项目是我们自动化工具箱的“前辈”，看看它们的 Star 数和定位，
从中找架构、功能、界面的灵感。
"""

# 导入 requests：发网络请求
import requests

# 要查询的知名项目（仓库全名 = 用户名/仓库名）
# 这些是根据第一轮搜索发现 + 行业常识挑选的“同类优秀项目”
REPOS = [
    # --- 工作流/自动化引擎 ---
    "n8n-io/n8n",                # 最流行的自托管工作流自动化（类 Zapier）
    "node-red/node-red",         # IBM 开源的流式可视化编程工具
    "huginn/huginn",             # “个人 Agent”：监控网页/邮件变化触发动作
    "activepieces/activepieces", # AI 优先的工作流平台
    # --- 文件自动化 ---
    "tfeldmann/organize",        # Python 写的文件整理工具（规则 DSL）
    # --- 无代码爬虫 ---
    "NaiboWang/EasySpider",      # 可视化无代码爬虫（第一轮已搜到，补详情）
]


def fetch_repo(full_name: str) -> dict | None:
    """按仓库名查一个项目的信息。"""
    # GitHub 单仓库接口：/repos/用户名/仓库名
    url = f"https://api.github.com/repos/{full_name}"
    # User-Agent 头必须带
    headers = {"User-Agent": "autobox-research"}
    # 发请求
    resp = requests.get(url, headers=headers, timeout=15)
    # 404 = 仓库不存在；其他错误抛异常
    if resp.status_code == 404:
        return None
    # 非 200 抛异常
    resp.raise_for_status()
    # 返回仓库信息
    return resp.json()


def main() -> None:
    """逐个查询并打印。"""
    # 遍历每个项目
    for repo in REPOS:
        # 尝试查询
        try:
            # 拿仓库信息
            data = fetch_repo(repo)
            # 不存在就提示
            if data is None:
                print(f"  (仓库不存在) {repo}")
                continue
            # 提取关键信息：star 数、简介、语言、创建时间
            stars = data["stargazers_count"]
            desc = (data.get("description") or "无简介")[:110]
            lang = data.get("language") or "?"
            created = data.get("created_at", "")[:10]  # 只取日期部分
            # 打印
            print(f"  ⭐{stars:>6}  {repo}  [{lang}, {created}]")
            print(f"           {desc}")
        except Exception as e:  # noqa: BLE001
            # 出错提示
            print(f"  {repo}: 查询失败 {e}")
        # 打印空行分隔
        print()


if __name__ == "__main__":
    main()
