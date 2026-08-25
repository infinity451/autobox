# -*- coding: utf-8 -*-
"""宏存储：对数据库里的宏做增删改查（CRUD）。

一个宏 = 一个名字 + 一串事件（鼠标键盘操作记录）：
{
  "id": "ab12cd34",
  "name": "打开记事本打字",
  "events": [
    {"type": "move",  "x": 100, "y": 200, "delay": 0.5},
    {"type": "click", "button": "left", "pressed": true, "x": 100, "y": 200, "delay": 0.1},
    {"type": "key",   "key": "a", "pressed": true, "delay": 0.05},
    ...
  ],
  "created_at": "...", "updated_at": "..."
}
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 json：事件列表在数据库里是 JSON 文本
import json

# 导入数据库模块
from .. import database


def _row_to_macro(row) -> dict:
    """数据库一行 → 宏字典。"""
    return {
        "id": row["id"],
        "name": row["name"],
        "events": json.loads(row["events"]),   # JSON 文本 → 事件列表
        "event_count": len(json.loads(row["events"])),  # 事件数量（列表显示用）
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_macros() -> list[dict]:
    """查询所有宏（新创建的在前）。"""
    rows = database.query("SELECT * FROM macros ORDER BY created_at DESC")
    return [_row_to_macro(r) for r in rows]


def get_macro(macro_id: str) -> dict | None:
    """按 id 查单个宏；不存在返回 None。"""
    rows = database.query("SELECT * FROM macros WHERE id = ?", (macro_id,))
    return _row_to_macro(rows[0]) if rows else None


def save_macro(name: str, events: list) -> dict:
    """保存一个宏（新建）。events 不能为空。"""
    from ..models import new_id, now_str

    # 名字不能为空
    if not name.strip():
        raise ValueError("宏名字不能为空")
    # 事件不能为空（没有事件的宏没意义）
    if not events:
        raise ValueError("宏没有事件，先录制或手动添加事件再保存")

    # 组装宏
    macro = {
        "id": new_id(),
        "name": name.strip(),
        "events": events,
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    # 存库；events 转 JSON 文本
    database.execute(
        "INSERT INTO macros (id, name, events, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (macro["id"], macro["name"], json.dumps(events, ensure_ascii=False),
         macro["created_at"], macro["updated_at"]),
    )
    return macro


def update_macro(macro_id: str, name: str, events: list) -> dict | None:
    """更新一个宏；不存在返回 None。"""
    old = get_macro(macro_id)
    if old is None:
        return None
    if not name.strip():
        raise ValueError("宏名字不能为空")
    if not events:
        raise ValueError("宏没有事件")

    from datetime import datetime

    macro = {
        "id": macro_id,
        "name": name.strip(),
        "events": events,
        "created_at": old["created_at"],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    database.execute(
        "UPDATE macros SET name=?, events=?, updated_at=? WHERE id=?",
        (macro["name"], json.dumps(events, ensure_ascii=False), macro["updated_at"], macro_id),
    )
    return macro


def delete_macro(macro_id: str) -> bool:
    """删除宏；返回是否真的删掉。"""
    if get_macro(macro_id) is None:
        return False
    database.execute("DELETE FROM macros WHERE id = ?", (macro_id,))
    return True
