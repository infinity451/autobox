# -*- coding: utf-8 -*-
"""采集执行器：跑一次采集 → 存 CSV → 记运行记录，还负责定时自动采集。

流程（手动运行一条任务）：
1. 从数据库拿任务配置
2. fetcher.fetch_html() 抓网页
3. fetcher.parse_items() 按选择器提取数据
4. 把数据写进 CSV 文件（data/exports/ 目录）
5. 把运行结果记进 crawl_runs 表（前端显示历史）
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 csv：写 CSV 文件（表格文件，Excel 能打开）
import csv
# 导入 json：任务字段配置解析
import json
# 导入 Path：路径处理
from pathlib import Path

# 导入数据库模块（查任务、写运行记录）
from .. import database
# 导入统一路径工具（数据目录在开发/打包两种模式下都正确）
from ..paths import data_dir
# 导入抓取解析引擎
from .fetcher import fetch_html, parse_items
# 导入任务管理（查任务）
from .tasks import get_task

# 导出目录：数据目录/exports/（CSV 文件都放这里）
# 用统一路径工具而不是相对 __file__ 拼路径（打包成 exe 后也能正确找到）
EXPORT_DIR = data_dir() / "exports"


def _write_csv(path: Path, fieldnames: list[str], records: list[dict]) -> None:
    """把记录列表写成 CSV 文件。

    注意：用 utf-8-sig 编码（带 BOM 标记）—— 这是给普通用户的关键细节：
    Excel 打开 utf-8 的 CSV 会乱码，但 utf-8-sig（带 BOM）就不会。
    """
    # 打开文件写模式，newline="" 防止 Windows 下 CSV 多出空行
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        # DictWriter：按字段名写字典列表
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        # 先写表头（第一行是列名）
        writer.writeheader()
        # 再写数据行
        writer.writerows(records)


def run_task(task_id: str) -> dict:
    """执行一次采集任务。返回结果字典（给 API/前端显示）。

    返回示例：
        {"ok": true, "count": 10, "csv": "任务名_时间.csv", "preview": [{...}, ...]}
    """
    # 从数据库拿任务；找不到直接返回失败
    task = get_task(task_id)
    if task is None:
        return {"ok": False, "error": "任务不存在"}

    # 任务名（日志和文件名要用）
    name = task["name"]
    # 字段配置
    fields = task["fields"]
    # 字段名列表（CSV 表头用）
    fieldnames = [f["name"] for f in fields]

    # 执行采集；出错要记录并返回，不能让整个程序崩溃
    try:
        # 第一步：抓网页
        html = fetch_html(task["url"])
        # 第二步：解析提取记录
        records = parse_items(html, task["item_selector"], fields, task["max_items"])
    except Exception as e:  # noqa: BLE001
        # 抓取/解析失败：记录失败日志
        _record_run(task, "error", 0, "", f"采集失败: {e}")
        # 返回失败结果
        return {"ok": False, "error": f"采集失败: {e}"}

    # 导出目录不存在就创建
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    # 生成文件名：任务名_时间戳.csv（时间戳精确到秒，不会重名）
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{ts}.csv"
    # 完整路径
    file_path = EXPORT_DIR / filename

    # 有数据才写 CSV；一条都没有就提示（可能是选择器写错了）
    if records:
        # 第三步：写 CSV
        _write_csv(file_path, fieldnames, records)
    else:
        # 没采到数据：不生成文件，记录提示
        _record_run(task, "error", 0, "", "没有采到数据，请检查选择器是否写对")
        return {"ok": False, "error": "没有采到数据，请检查选择器是否写对"}

    # 第四步：记录成功运行
    _record_run(task, "success", len(records), filename, f"采集到 {len(records)} 条")
    # 返回成功结果（前 5 条预览给前端表格显示）
    return {"ok": True, "count": len(records), "csv": filename, "preview": records[:5]}


def _record_run(task: dict, status: str, count: int, csv_file: str, message: str) -> None:
    """把一次运行结果写进 crawl_runs 表。"""
    # 导入 models 的 now_str（当前时间字符串）
    from ..models import now_str

    # 插入运行记录
    database.execute(
        "INSERT INTO crawl_runs (task_id, task_name, status, item_count, csv_file, message, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task["id"], task["name"], status, count, csv_file, message, now_str()),
    )


def list_runs(task_id: str | None = None, limit: int = 50) -> list[dict]:
    """查询运行历史（可按任务过滤，默认返回最近 50 条）。"""
    # 按任务过滤还是查全部
    if task_id:
        # 带任务过滤：按时间倒序取前 limit 条
        rows = database.query(
            "SELECT * FROM crawl_runs WHERE task_id = ? ORDER BY id DESC LIMIT ?",
            (task_id, limit),
        )
    else:
        rows = database.query(
            "SELECT * FROM crawl_runs ORDER BY id DESC LIMIT ?", (limit,)
        )
    # 每行转成字典
    return [
        {
            "task_name": r["task_name"],
            "status": r["status"],
            "item_count": r["item_count"],
            "csv_file": r["csv_file"],
            "message": r["message"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# ---------- 定时自动采集 ----------

# 记录已注册的定时任务：{任务id: 是否已注册}，防止重复注册
_scheduled: dict[str, bool] = {}


def schedule_task(task: dict) -> None:
    """给任务注册定时采集（任务配置了 cron 且启用时）。

    到点后自动执行 run_task。
    """
    # 导入触发器模块（复用 APScheduler 定时器）
    from ..engine import triggers

    # 任务没有 cron 表达式 → 不需要定时，直接返回
    if not task.get("cron"):
        return
    # 已经在注册表里 → 不重复注册
    if _scheduled.get(task["id"]):
        return
    # 注册定时任务：job id 用任务 id（方便更新/删除）
    # 到点调用 run_task(任务id)
    triggers.add_cron_job(
        lambda tid=task["id"]: run_task(tid),
        job_id=f"crawl_{task['id']}",
        cron=task["cron"],
    )
    # 标记已注册
    _scheduled[task["id"]] = True


def unschedule_task(task_id: str) -> None:
    """取消任务的定时采集（任务被删/暂停时调用）。"""
    # 导入触发器模块
    from ..engine import triggers

    # 删除定时任务（job id 格式 crawl_任务id）
    triggers.remove_job(f"crawl_{task_id}")
    # 从注册表移除
    _scheduled.pop(task_id, None)


def sync_schedules() -> None:
    """同步所有任务的定时配置：扫描数据库，注册/取消定时任务。

    什么时候调用：程序启动时、任务增删改后。
    简单粗暴的方式：把定时任务全部取消，再按最新配置全部重新注册。
    """
    # 导入任务管理（查全部任务）
    from .tasks import list_tasks

    # 把所有已注册的定时全部取消（清空重来）
    for tid in list(_scheduled.keys()):
        unschedule_task(tid)

    # 遍历所有任务，把“启用且有 cron”的重新注册
    for task in list_tasks():
        # 未启用的任务不参与定时
        if not task["enabled"]:
            continue
        # 有 cron 才注册
        if task.get("cron"):
            schedule_task(task)
