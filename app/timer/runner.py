# -*- coding: utf-8 -*-
"""定时任务执行器：到点执行动作 + 注册/取消定时。

动作执行（action 决定做什么）：
- notify    → 弹窗提醒（Windows 系统消息框）
- shutdown  → 定时关机（60 秒缓冲，给用户反悔时间）
- restart   → 定时重启
- sleep     → 休眠
- open      → 打开指定程序

调度：复用规则引擎的 APScheduler（triggers._scheduler），
任务配置 cron 后注册，到点自动执行。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 subprocess：调用外部命令（关机命令、打开程序）
import subprocess

# 导入数据库模块（写日志）
from .. import database
# 导入动作类型常量
from .tasks import (
    ACTION_NOTIFY,
    ACTION_OPEN,
    ACTION_RESTART,
    ACTION_SHUTDOWN,
    ACTION_SLEEP,
    get_task,
)


def show_notify(title: str, message: str) -> None:
    """弹出一个 Windows 系统消息框（提醒用户）。

    原理：用 ctypes 直接调用 Windows 自带的 API（MessageBoxW），
    不需要装任何第三方库，所有 Windows 电脑都能用。
    """
    try:
        # 导入 ctypes：Python 调用 C 语言函数库的工具（Windows API 就是 C 接口）
        import ctypes
        # 调用系统消息框：
        # MessageBoxW(0, 内容, 标题, 图标代码)
        # 0x40 = 蓝色信息图标（不是错误图标，避免吓人）
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
    except Exception:  # noqa: BLE001
        # 弹窗失败（极少数环境限制）：退而求其次，写日志提醒
        database.log(None, "定时提醒", "warn", f"弹窗失败，原提醒内容: {message}")


def execute_action(task: dict) -> str:
    """执行一个定时任务的动作。返回执行结果说明（用于写日志）。

    参数：
        task: 任务字典
    返回：
        说明文字（成功/失败信息）
    """
    # 任务名和动作类型
    name = task["name"]
    action = task["action"]

    # 按动作类型分派
    if action == ACTION_NOTIFY:
        # 弹窗提醒：标题用任务名，内容用配置的消息
        show_notify(name, task.get("message") or "时间到啦")
        # 返回说明
        return f"已弹出提醒: {task.get('message')}"

    if action == ACTION_SHUTDOWN:
        # 定时关机：shutdown /s = 关机，/t 60 = 60 秒后执行（给用户反悔时间）
        # 注意：不要直接关，60 秒内用户还能用 shutdown /a 取消
        subprocess.run(["shutdown", "/s", "/t", "60"], check=False)
        return "已发送关机指令（60 秒后关机，可用 shutdown /a 取消）"

    if action == ACTION_RESTART:
        # 定时重启：/r = 重启
        subprocess.run(["shutdown", "/r", "/t", "60"], check=False)
        return "已发送重启指令（60 秒后重启）"

    if action == ACTION_SLEEP:
        # 休眠：/h = 休眠
        subprocess.run(["shutdown", "/h"], check=False)
        return "已发送休眠指令"

    if action == ACTION_OPEN:
        # 打开程序：subprocess.Popen 启动指定程序
        # Popen 不会等待程序关闭（打开记事本不阻塞定时器）
        subprocess.Popen([task.get("program", "")], shell=False)
        return f"已启动程序: {task.get('program')}"

    # 未知动作（理论上校验已挡掉）
    return f"未知动作类型: {action}"


def run_task(task_id: str) -> dict:
    """执行一个定时任务（到点被调度器调用 / 手动测试用）。"""
    # 查任务
    task = get_task(task_id)
    if task is None:
        return {"ok": False, "error": "任务不存在"}

    # 执行动作；出错记录日志不崩溃
    try:
        message = execute_action(task)
        # 记成功日志
        database.log(task_id, task["name"], "success", message)
        return {"ok": True, "message": message}
    except Exception as e:  # noqa: BLE001
        # 记错误日志
        database.log(task_id, task["name"], "error", f"执行失败: {e}")
        return {"ok": False, "error": str(e)}


# ---------- 定时调度 ----------

# 记录已注册的任务：{任务id: True}，防止重复注册
_scheduled: dict[str, bool] = {}


def schedule_task(task: dict) -> None:
    """注册任务的定时调度（到点执行 run_task）。"""
    from ..engine import triggers

    # 没有 cron 就不用定时
    if not task.get("cron"):
        return
    # 已注册过就不重复
    if _scheduled.get(task["id"]):
        return
    # 注册：job id 用 timer_任务id（与其他模块的定时任务区分）
    triggers.add_cron_job(
        lambda tid=task["id"]: run_task(tid),
        job_id=f"timer_{task['id']}",
        cron=task["cron"],
    )
    # 标记已注册
    _scheduled[task["id"]] = True


def unschedule_task(task_id: str) -> None:
    """取消任务的定时调度。"""
    from ..engine import triggers

    # 删除定时任务
    triggers.remove_job(f"timer_{task_id}")
    # 从注册表移除
    _scheduled.pop(task_id, None)


def sync_schedules() -> None:
    """同步所有定时任务的调度（启动时、任务增删改后调用）。"""
    from .tasks import list_tasks

    # 全部取消，再按最新配置重注册（简单粗暴但可靠）
    for tid in list(_scheduled.keys()):
        unschedule_task(tid)

    # 遍历任务，注册"启用且有 cron"的
    for task in list_tasks():
        if task["enabled"] and task.get("cron"):
            schedule_task(task)
