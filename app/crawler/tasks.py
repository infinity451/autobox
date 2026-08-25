# -*- coding: utf-8 -*-
"""采集任务管理：对数据库里的采集任务做增删改查（CRUD）。

一个采集任务长这样（数据库里存 JSON 文本）：

{
  "id": "ab12cd34",                # 唯一编号
  "name": "新闻标题采集",           # 任务名字
  "url": "https://example.com",    # 要采集的网页
  "item_selector": "div.news-item",# 列表容器选择器：每个 div.news-item 是一条记录
  "fields": [                      # 要提取的字段列表
    {"name": "标题", "selector": "h2", "attr": "text"},   # 取 h2 的文本
    {"name": "链接", "selector": "a", "attr": "attr.href"} # 取 a 的 href 属性
  ],
  "cron": "",                      # 定时表达式（空 = 不自动采集）
  "max_items": 50,                 # 最多采集 50 条
  "enabled": true                  # 是否启用
}
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 json：字典和 JSON 文本互转（任务里的 fields 在数据库里是 JSON 文本）
import json

# 导入数据库模块
from .. import database


def _row_to_task(row) -> dict:
    """把数据库一行数据转成任务字典。"""
    return {
        "id": row["id"],                                 # 编号
        "name": row["name"],                             # 名字
        "url": row["url"],                               # 网址
        "item_selector": row["item_selector"],           # 列表容器选择器
        "fields": json.loads(row["fields"]),             # 字段列表（JSON→列表）
        "cron": row["cron"],                             # 定时表达式
        "max_items": row["max_items"],                   # 最多条数
        "enabled": bool(row["enabled"]),                 # 是否启用
        "created_at": row["created_at"],                 # 创建时间
        "updated_at": row["updated_at"],                 # 更新时间
    }


def list_tasks() -> list[dict]:
    """查询所有采集任务（按创建时间倒序）。"""
    # 查表；ORDER BY created_at DESC = 按创建时间倒序（新的在前）
    rows = database.query("SELECT * FROM crawler_tasks ORDER BY created_at DESC")
    # 每行转成字典返回
    return [_row_to_task(r) for r in rows]


def get_task(task_id: str) -> dict | None:
    """按 id 查单个任务；找不到返回 None。"""
    # 按 id 精确查询
    rows = database.query("SELECT * FROM crawler_tasks WHERE id = ?", (task_id,))
    # 有结果返回，没有返回 None
    return _row_to_task(rows[0]) if rows else None


def validate_task(task: dict) -> str | None:
    """校验任务配置是否合法。返回 None 表示合法，字符串表示错误原因。"""
    # 名字不能为空
    if not task.get("name", "").strip():
        return "任务名字不能为空"
    # 网址必须是以 http:// 或 https:// 开头
    url = task.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return "网址必须以 http:// 或 https:// 开头"
    # 列表容器选择器不能为空
    if not task.get("item_selector", "").strip():
        return "列表容器选择器不能为空（CSS 选择器，如 div.news-item）"
    # 至少需要一个字段
    if not task.get("fields"):
        return "至少需要一个提取字段"
    # 每个字段要有名字和选择器
    for f in task["fields"]:
        if not f.get("name", "").strip():
            return "字段名不能为空"
        if not f.get("selector", "").strip():
            return "字段选择器不能为空"
        # attr 默认为 text（取文本）
        f.setdefault("attr", "text")
    # 最多条数要是正整数（小于 1 就给 50）
    if task.get("max_items", 0) < 1:
        task["max_items"] = 50
    # 校验通过
    return None


def create_task(name: str, url: str, item_selector: str, fields: list,
                cron: str = "", max_items: int = 50, enabled: bool = True) -> dict:
    """创建一条采集任务。校验不通过时抛 ValueError。"""
    # 导入 models 的 new_id / now_str（生成编号和时间）
    from ..models import new_id, now_str

    # 组装任务字典
    task = {
        "id": new_id(),                # 自动生成编号
        "name": name.strip(),          # 去掉首尾空格
        "url": url.strip(),
        "item_selector": item_selector.strip(),
        "fields": fields,
        "cron": cron.strip(),
        "max_items": max_items,
        "enabled": enabled,
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    # 校验；不合法抛异常（API 层捕获返回给前端）
    error = validate_task(task)
    if error:
        raise ValueError(error)

    # 存数据库；fields 转成 JSON 文本
    database.execute(
        "INSERT INTO crawler_tasks "
        "(id, name, url, item_selector, fields, cron, max_items, enabled, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            task["id"], task["name"], task["url"], task["item_selector"],
            json.dumps(fields, ensure_ascii=False),       # ensure_ascii=False 中文原样存
            task["cron"], task["max_items"],
            1 if enabled else 0,                          # True→1，False→0
            task["created_at"], task["updated_at"],
        ),
    )
    # 返回创建好的任务
    return task


def update_task(task_id: str, name: str, url: str, item_selector: str, fields: list,
                cron: str = "", max_items: int = 50, enabled: bool = True) -> dict | None:
    """更新一条采集任务。任务不存在返回 None。"""
    # 查一下原任务（拿创建时间）
    old = get_task(task_id)
    if old is None:
        return None

    # 组装新任务（id 和创建时间沿用旧值，更新时间刷新）
    task = {
        "id": task_id,
        "name": name.strip(),
        "url": url.strip(),
        "item_selector": item_selector.strip(),
        "fields": fields,
        "cron": cron.strip(),
        "max_items": max_items,
        "enabled": enabled,
        "created_at": old["created_at"],
        "updated_at": old["updated_at"],   # 用旧值占位，下面会刷新
    }
    # 刷新更新时间
    from datetime import datetime

    task["updated_at"] = datetime.now().isoformat(timespec="seconds")
    # 校验
    error = validate_task(task)
    if error:
        raise ValueError(error)

    # 执行更新
    database.execute(
        "UPDATE crawler_tasks SET name=?, url=?, item_selector=?, fields=?, cron=?, "
        "max_items=?, enabled=?, updated_at=? WHERE id=?",
        (
            task["name"], task["url"], task["item_selector"],
            json.dumps(fields, ensure_ascii=False), task["cron"], task["max_items"],
            1 if enabled else 0, task["updated_at"], task_id,
        ),
    )
    # 返回更新后的任务
    return task


def delete_task(task_id: str) -> bool:
    """删除任务。返回是否真的删掉了。"""
    # 不存在就返回 False
    if get_task(task_id) is None:
        return False
    # 删除记录
    database.execute("DELETE FROM crawler_tasks WHERE id = ?", (task_id,))
    # 删除关联的运行记录（历史一起清掉，保持干净）
    database.execute("DELETE FROM crawl_runs WHERE task_id = ?", (task_id,))
    # 返回删除成功
    return True


def toggle_task(task_id: str) -> dict | None:
    """切换启用/暂停。返回切换后的任务；不存在返回 None。"""
    # 查任务
    task = get_task(task_id)
    if task is None:
        return None
    # 取反后更新
    return update_task(
        task_id,
        task["name"], task["url"], task["item_selector"], task["fields"],
        task["cron"], task["max_items"], not task["enabled"],
    )
