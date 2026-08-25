# -*- coding: utf-8 -*-
"""定时任务管理：对数据库里的定时任务做增删改查（CRUD）。

一个定时任务长这样：

{
  "id": "ab12cd34",
  "name": "喝水提醒",
  "action": "notify",            # 做什么：notify 提醒 / shutdown 关机 / restart 重启 / sleep 休眠 / open 打开程序
  "cron": "0 9 * * *",           # 什么时候：每天 9 点
  "message": "该喝水啦",
  "program": "",                 # action 是 open 时：要打开的程序路径
  "enabled": true
}
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入数据库模块
from .. import database

# 动作类型常量（前端下拉框的 value 用）
ACTION_NOTIFY = "notify"      # 弹窗提醒
ACTION_SHUTDOWN = "shutdown"  # 定时关机
ACTION_RESTART = "restart"    # 定时重启
ACTION_SLEEP = "sleep"        # 定时休眠
ACTION_OPEN = "open"          # 定时打开程序

# 所有合法动作类型（校验用）
ACTION_TYPES = [ACTION_NOTIFY, ACTION_SHUTDOWN, ACTION_RESTART, ACTION_SLEEP, ACTION_OPEN]


def _row_to_task(row) -> dict:
    """数据库一行 → 任务字典。"""
    return {
        "id": row["id"],
        "name": row["name"],
        "action": row["action"],
        "cron": row["cron"],
        "message": row["message"],
        "program": row["program"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_tasks() -> list[dict]:
    """查询所有定时任务（新创建的在前）。"""
    rows = database.query("SELECT * FROM timer_tasks ORDER BY created_at DESC")
    return [_row_to_task(r) for r in rows]


def get_task(task_id: str) -> dict | None:
    """按 id 查单个任务；找不到返回 None。"""
    rows = database.query("SELECT * FROM timer_tasks WHERE id = ?", (task_id,))
    return _row_to_task(rows[0]) if rows else None


def validate_task(task: dict) -> str | None:
    """校验任务配置。返回 None 合法，字符串为错误原因。"""
    # 名字不能为空
    if not task.get("name", "").strip():
        return "任务名字不能为空"
    # 动作类型必须合法
    if task.get("action") not in ACTION_TYPES:
        return "动作类型无效"
    # cron 表达式不能为空（定时任务必须有时间）
    if not task.get("cron", "").strip():
        return "cron 表达式不能为空（如 0 9 * * * = 每天 9 点）"
    # 提醒类必须有消息内容
    if task["action"] == ACTION_NOTIFY and not task.get("message", "").strip():
        return "提醒任务必须填写提醒内容"
    # 打开程序类必须有程序路径
    if task["action"] == ACTION_OPEN and not task.get("program", "").strip():
        return "打开程序任务必须填写程序路径"
    return None


def create_task(name: str, action: str, cron: str, message: str = "",
                program: str = "", enabled: bool = True) -> dict:
    """创建定时任务。"""
    from ..models import new_id, now_str

    task = {
        "id": new_id(),
        "name": name.strip(),
        "action": action,
        "cron": cron.strip(),
        "message": message.strip(),
        "program": program.strip(),
        "enabled": enabled,
        "created_at": now_str(),
        "updated_at": now_str(),
    }
    error = validate_task(task)
    if error:
        raise ValueError(error)

    database.execute(
        "INSERT INTO timer_tasks (id, name, action, cron, message, program, enabled, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (task["id"], task["name"], task["action"], task["cron"],
         task["message"], task["program"], 1 if enabled else 0,
         task["created_at"], task["updated_at"]),
    )
    return task


def update_task(task_id: str, name: str, action: str, cron: str, message: str = "",
                program: str = "", enabled: bool = True) -> dict | None:
    """更新定时任务；不存在返回 None。"""
    old = get_task(task_id)
    if old is None:
        return None

    from datetime import datetime

    task = {
        "id": task_id,
        "name": name.strip(),
        "action": action,
        "cron": cron.strip(),
        "message": message.strip(),
        "program": program.strip(),
        "enabled": enabled,
        "created_at": old["created_at"],
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    error = validate_task(task)
    if error:
        raise ValueError(error)

    database.execute(
        "UPDATE timer_tasks SET name=?, action=?, cron=?, message=?, program=?, enabled=?, updated_at=? WHERE id=?",
        (task["name"], task["action"], task["cron"], task["message"],
         task["program"], 1 if enabled else 0, task["updated_at"], task_id),
    )
    return task


def delete_task(task_id: str) -> bool:
    """删除任务；返回是否真的删掉。"""
    if get_task(task_id) is None:
        return False
    database.execute("DELETE FROM timer_tasks WHERE id = ?", (task_id,))
    return True


def toggle_task(task_id: str) -> dict | None:
    """切换启用/暂停。"""
    task = get_task(task_id)
    if task is None:
        return None
    return update_task(
        task_id, task["name"], task["action"], task["cron"],
        task["message"], task["program"], not task["enabled"],
    )
