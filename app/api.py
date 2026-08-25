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
