# -*- coding: utf-8 -*-
"""API 层：网页前端和引擎之间的“翻译官”。

前端页面（浏览器里的 JS）不能直接操作 Python 代码，
它通过 HTTP 请求（网址）来调用这里定义的接口：
    GET    /api/rules           → 获取规则列表
    POST   /api/rules           → 创建规则
    PUT    /api/rules/{id}      → 更新规则
    DELETE /api/rules/{id}      → 删除规则
    POST   /api/rules/{id}/toggle → 启用/暂停切换
    GET    /api/logs            → 获取运行日志
    GET    /api/status          → 获取引擎状态
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 FastAPI 的依赖：
# APIRouter 用来把接口分组注册到应用上
# HTTPException 用来返回“错误响应”（比如规则不存在时返回 404）
from fastapi import APIRouter, HTTPException
# 导入 pydantic 的 BaseModel：用来定义“接口收到的数据长什么样”，
# 前端传过来的数据会自动按这个格式校验，字段类型不对会自动报错
from pydantic import BaseModel

# 导入数据库模块（查日志）
from . import database
# 导入规则管理函数
from .engine.rules import create_rule, delete_rule, get_rule, list_rules, toggle_rule, update_rule
# 导入全局引擎单例
from .engine.scheduler import engine

# 创建一个路由器对象（把接口挂到 main.py 的应用上）
router = APIRouter(prefix="/api")


# ---------- 定义“接口数据结构”（Pydantic 模型） ----------

class TriggerIn(BaseModel):
    """触发器（前端传来的数据）。"""
    type: str          # 类型：file_added / file_modified / schedule
    watch_dir: str = ""  # 监控目录（文件类触发器用；默认空字符串）
    cron: str = ""     # cron 表达式（定时触发器用；默认空字符串）


class ConditionIn(BaseModel):
    """条件（前端传来的数据）。"""
    field: str         # 字段：name / ext / size / path
    op: str            # 操作符：contains / equals / in / gt / lt
    value: object      # 值：字符串或列表（object 表示任意类型）


class ActionIn(BaseModel):
    """动作（前端传来的数据）。"""
    type: str                 # 类型：move / copy / rename / notify
    dest_dir: str = ""        # 目标目录（移动/复制用）
    new_name: str = ""        # 新文件名（重命名用）
    message: str = ""         # 通知内容（通知用）


class RuleIn(BaseModel):
    """创建/更新规则时前端传的完整数据。"""
    name: str                       # 规则名字
    trigger: TriggerIn              # 触发器
    conditions: list[ConditionIn] = []   # 条件列表（默认空）
    actions: list[ActionIn]         # 动作列表
    enabled: bool = True            # 是否启用（默认启用）


# ---------- 接口实现 ----------

@router.get("/rules")
def api_list_rules() -> dict:
    """接口：获取所有规则。"""
    # 返回 {"rules": [...]}，前端拿到后渲染列表
    return {"rules": list_rules()}


@router.post("/rules")
def api_create_rule(data: RuleIn) -> dict:
    """接口：创建一条新规则。"""
    # 把 Pydantic 模型转成普通字典（.model_dump() 是 Pydantic 的方法）
    # 然后调用 create_rule 存进数据库
    try:
        # 组装规则字典传给 create_rule
        rule = create_rule(
            name=data.name,
            trigger=data.trigger.model_dump(),
            conditions=[c.model_dump() for c in data.conditions],
            actions=[a.model_dump() for a in data.actions],
            enabled=data.enabled,
        )
    except ValueError as e:
        # 规则不合法：返回 400 错误（Bad Request），错误信息显示给用户
        raise HTTPException(status_code=400, detail=str(e))

    # 创建成功后刷新引擎（让它立即监听新规则）
    engine.refresh()
    # 返回创建好的规则
    return {"rule": rule}


@router.put("/rules/{rule_id}")
def api_update_rule(rule_id: str, data: RuleIn) -> dict:
    """接口：更新一条规则。"""
    # 调用 update_rule；规则不存在时返回 None
    rule = update_rule(
        rule_id,
        name=data.name,
        trigger=data.trigger.model_dump(),
        conditions=[c.model_dump() for c in data.conditions],
        actions=[a.model_dump() for a in data.actions],
        enabled=data.enabled,
    )
    # 规则不存在：返回 404（Not Found）
    if rule is None:
        raise HTTPException(status_code=404, detail="规则不存在")
    # 更新成功后刷新引擎
    engine.refresh()
    # 返回更新后的规则
    return {"rule": rule}


@router.delete("/rules/{rule_id}")
def api_delete_rule(rule_id: str) -> dict:
    """接口：删除一条规则。"""
    # 调用 delete_rule；返回 False 表示规则不存在
    if not delete_rule(rule_id):
        # 规则不存在：返回 404
        raise HTTPException(status_code=404, detail="规则不存在")
    # 删除成功后刷新引擎（停止对应监控/定时任务）
    engine.refresh()
    # 返回删除成功
    return {"ok": True}


@router.post("/rules/{rule_id}/toggle")
def api_toggle_rule(rule_id: str) -> dict:
    """接口：切换规则的启用/暂停状态。"""
    # 调用 toggle_rule；返回 None 表示规则不存在
    rule = toggle_rule(rule_id)
    if rule is None:
        # 规则不存在：返回 404
        raise HTTPException(status_code=404, detail="规则不存在")
    # 切换成功后刷新引擎（启用则开始监控，暂停则停止）
    engine.refresh()
    # 返回切换后的规则
    return {"rule": rule}


@router.get("/logs")
def api_logs(limit: int = 100) -> dict:
    """接口：获取最近的运行日志。

    参数：
        limit: 最多返回多少条（默认 100），防止一次返回太多
    """
    # 查数据库：按时间倒序，取前 limit 条
    rows = database.query(
        "SELECT rule_name, level, message, created_at FROM run_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    # 把每行转成字典列表返回
    logs = [
        {"rule": r["rule_name"], "level": r["level"], "message": r["message"], "time": r["created_at"]}
        for r in rows
    ]
    # 返回日志列表
    return {"logs": logs}


@router.get("/status")
def api_status() -> dict:
    """接口：获取引擎状态（网页首页显示用）。"""
    # 返回：启用规则数、引擎是否运行中
    return {
        "rules_enabled": len(engine.rules),   # 当前加载的启用规则数
        "running": engine._started,           # 引擎是否在运行
        "version": "0.1.0",                   # 项目版本
    }


# ============================================================
# 网页采集器接口（第 2 阶段）
# ============================================================

# 导入采集器模块（任务管理、执行器）
from .crawler.tasks import (
    create_task as crawler_create_task,
    delete_task as crawler_delete_task,
    list_tasks as crawler_list_tasks,
    toggle_task as crawler_toggle_task,
    update_task as crawler_update_task,
)
from .crawler.runner import list_runs, run_task, sync_schedules


class CrawlFieldIn(BaseModel):
    """采集字段配置（前端传来的数据）。"""
    name: str                    # 字段名（CSV 的列名）
    selector: str                # CSS 选择器（怎么定位这个字段）
    attr: str = "text"           # 取值方式：text / html / attr.xxx


class CrawlTaskIn(BaseModel):
    """采集任务（前端传来的数据）。"""
    name: str                    # 任务名字
    url: str                     # 网页地址
    item_selector: str           # 列表容器选择器
    fields: list[CrawlFieldIn]   # 字段列表
    cron: str = ""               # 定时表达式（空 = 不自动）
    max_items: int = 50          # 最多条数
    enabled: bool = True         # 是否启用


@router.get("/crawl/tasks")
def api_crawl_list() -> dict:
    """接口：获取所有采集任务。"""
    return {"tasks": crawler_list_tasks()}


@router.post("/crawl/tasks")
def api_crawl_create(data: CrawlTaskIn) -> dict:
    """接口：创建采集任务。"""
    try:
        task = crawler_create_task(
            name=data.name,
            url=data.url,
            item_selector=data.item_selector,
            fields=[f.model_dump() for f in data.fields],
            cron=data.cron,
            max_items=data.max_items,
            enabled=data.enabled,
        )
    except ValueError as e:
        # 校验失败返回 400
        raise HTTPException(status_code=400, detail=str(e))
    # 同步定时任务（新任务可能带 cron）
    sync_schedules()
    return {"task": task}


@router.put("/crawl/tasks/{task_id}")
def api_crawl_update(task_id: str, data: CrawlTaskIn) -> dict:
    """接口：更新采集任务。"""
    try:
        task = crawler_update_task(
            task_id,
            name=data.name,
            url=data.url,
            item_selector=data.item_selector,
            fields=[f.model_dump() for f in data.fields],
            cron=data.cron,
            max_items=data.max_items,
            enabled=data.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    sync_schedules()
    return {"task": task}


@router.delete("/crawl/tasks/{task_id}")
def api_crawl_delete(task_id: str) -> dict:
    """接口：删除采集任务。"""
    if not crawler_delete_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    sync_schedules()
    return {"ok": True}


@router.post("/crawl/tasks/{task_id}/toggle")
def api_crawl_toggle(task_id: str) -> dict:
    """接口：切换任务启用/暂停。"""
    task = crawler_toggle_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    sync_schedules()
    return {"task": task}


@router.post("/crawl/tasks/{task_id}/run")
def api_crawl_run(task_id: str) -> dict:
    """接口：立即执行一次采集。

    返回结果（ok/count/csv/preview），前端显示“采到几条 + 表格预览 + 下载链接”。
    """
    return run_task(task_id)


@router.get("/crawl/runs")
def api_crawl_runs(task_id: str | None = None) -> dict:
    """接口：查询采集运行历史。"""
    return {"runs": list_runs(task_id)}


# ============================================================
# 批量文件魔法接口（第 3 阶段）
# ============================================================

# 导入批量重命名引擎
from .batch.rename import execute_rename, preview_rename


class BatchRenameIn(BaseModel):
    """批量重命名请求（前端传来的数据）。"""
    directory: str               # 要处理的文件夹
    mode: str                    # 模式：prefix/suffix/replace/sequence
    params: dict = {}            # 模式参数，如 {"prefix": "工作_"}
    max_items: int = 200         # 最多处理多少个文件


@router.post("/batch/rename/preview")
def api_batch_preview(data: BatchRenameIn) -> dict:
    """接口：预览重命名结果（不真正改名）。"""
    # 调用引擎的预览函数，返回 旧名→新名 对照表
    return preview_rename(data.directory, data.mode, data.params, data.max_items)


@router.post("/batch/rename/execute")
def api_batch_execute(data: BatchRenameIn) -> dict:
    """接口：执行重命名（真正改名）。"""
    return execute_rename(data.directory, data.mode, data.params, data.max_items)


# ============================================================
# 定时提醒中心接口（第 3 阶段）
# ============================================================

# 导入定时任务模块
from .timer.tasks import (
    create_task as timer_create_task,
    delete_task as timer_delete_task,
    list_tasks as timer_list_tasks,
    toggle_task as timer_toggle_task,
    update_task as timer_update_task,
)
from .timer.runner import run_task as timer_run_task, sync_schedules as timer_sync_schedules


class TimerTaskIn(BaseModel):
    """定时任务（前端传来的数据）。"""
    name: str                    # 任务名字
    action: str                  # 动作：notify/shutdown/restart/sleep/open
    cron: str                    # 定时表达式
    message: str = ""            # 提醒内容（notify 用）
    program: str = ""            # 程序路径（open 用）
    enabled: bool = True         # 是否启用


@router.get("/timer/tasks")
def api_timer_list() -> dict:
    """接口：获取所有定时任务。"""
    return {"tasks": timer_list_tasks()}


@router.post("/timer/tasks")
def api_timer_create(data: TimerTaskIn) -> dict:
    """接口：创建定时任务。"""
    try:
        task = timer_create_task(
            name=data.name,
            action=data.action,
            cron=data.cron,
            message=data.message,
            program=data.program,
            enabled=data.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    timer_sync_schedules()
    return {"task": task}


@router.put("/timer/tasks/{task_id}")
def api_timer_update(task_id: str, data: TimerTaskIn) -> dict:
    """接口：更新定时任务。"""
    try:
        task = timer_update_task(
            task_id,
            name=data.name,
            action=data.action,
            cron=data.cron,
            message=data.message,
            program=data.program,
            enabled=data.enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    timer_sync_schedules()
    return {"task": task}


@router.delete("/timer/tasks/{task_id}")
def api_timer_delete(task_id: str) -> dict:
    """接口：删除定时任务。"""
    if not timer_delete_task(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    timer_sync_schedules()
    return {"ok": True}


@router.post("/timer/tasks/{task_id}/toggle")
def api_timer_toggle(task_id: str) -> dict:
    """接口：切换任务启用/暂停。"""
    task = timer_toggle_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    timer_sync_schedules()
    return {"task": task}


@router.post("/timer/tasks/{task_id}/run")
def api_timer_run(task_id: str) -> dict:
    """接口：立即执行一次定时任务（测试弹窗用）。"""
    return timer_run_task(task_id)


# ============================================================
# 宏录制器接口（第 4 阶段）
# ============================================================

# 导入宏模块
from .macro.store import delete_macro, get_macro, list_macros, save_macro
from .macro.recorder import is_recording, start_recording, stop_recording
from .macro.player import is_playing, play_macro, stop_playing


class MacroSaveIn(BaseModel):
    """保存宏（前端传来的数据）。"""
    name: str        # 宏名字
    events: list     # 事件序列（录制得到的）


class MacroPlayIn(BaseModel):
    """回放请求（前端传来的数据）。"""
    speed: float = 1.0   # 速度倍率（1=原速）


@router.get("/macro/list")
def api_macro_list() -> dict:
    """接口：获取所有宏。"""
    return {"macros": list_macros()}


@router.post("/macro/save")
def api_macro_save(data: MacroSaveIn) -> dict:
    """接口：保存宏。"""
    try:
        macro = save_macro(data.name, data.events)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"macro": macro}


@router.delete("/macro/{macro_id}")
def api_macro_delete(macro_id: str) -> dict:
    """接口：删除宏。"""
    if not delete_macro(macro_id):
        raise HTTPException(status_code=404, detail="宏不存在")
    return {"ok": True}


@router.post("/macro/{macro_id}/play")
def api_macro_play(macro_id: str, data: MacroPlayIn) -> dict:
    """接口：回放宏（真的操作鼠标键盘）。

    注意：这是有实际副作用的操作（点鼠标/打字），前端应让用户确认。
    """
    # 查宏
    macro = get_macro(macro_id)
    if macro is None:
        raise HTTPException(status_code=404, detail="宏不存在")
    # 正在回放中就不能再回放（防止重复触发）
    if is_playing():
        return {"ok": False, "error": "正在回放中，请先停止"}
    # 执行回放
    return play_macro(macro["events"], speed=data.speed)


@router.post("/macro/play/stop")
def api_macro_play_stop() -> dict:
    """接口：请求停止回放（紧急停止）。"""
    stop_playing()
    return {"ok": True}


@router.post("/macro/record/start")
def api_macro_record_start() -> dict:
    """接口：开始录制。

    前端调用后，用户接下来操作的鼠标键盘都会被记录。
    注意：录制期间服务端会持续监听，前端需要再调 stop 结束。
    """
    start_recording()
    return {"ok": True, "recording": True}


@router.post("/macro/record/stop")
def api_macro_record_stop() -> dict:
    """接口：停止录制，返回录到的事件。"""
    events = stop_recording()
    return {"ok": True, "events": events, "count": len(events)}


@router.get("/macro/status")
def api_macro_status() -> dict:
    """接口：查询录制/回放状态（前端轮询用）。"""
    return {"recording": is_recording(), "playing": is_playing()}
