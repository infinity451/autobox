# -*- coding: utf-8 -*-
"""Web 应用工厂：创建 AutoBox 的 FastAPI 应用。

这是"软件的唯一后端"：
- 提供全部接口（规则/采集/批量/定时/宏）
- 托管静态页面（桌面窗口加载的就是这些页面）
- 管理生命周期（启动时初始化引擎，关闭时优雅清理）

desktop.py（桌面窗口）和调试入口都从这里拿 app，不再直接写第二份。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 FastAPI 框架核心类：
# FastAPI 是网页框架（提供接口服务），StaticFiles 用来托管静态文件（HTML/CSS/JS）
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
# 导入 contextlib 的 asynccontextmanager：实现"启动时初始化 / 关闭时清理"的钩子
from contextlib import asynccontextmanager

# 导入本项目模块：
# init_db：建表；engine：全局引擎单例；router：API 路由
from app.database import init_db
from app.engine.scheduler import engine
from app.api import router
# 导入统一路径工具（打包/开发两种模式都正确）
from app.paths import data_dir, resource_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理。

    yield 之前 = 服务启动时执行（初始化）
    yield 之后 = 服务关闭时执行（清理）
    """
    # ---------- 启动初始化 ----------
    # 确保数据目录存在（第一次运行会创建）
    data_dir().mkdir(parents=True, exist_ok=True)
    # 初始化数据库（建表；已经建过也没关系，幂等）
    init_db()
    # 启动自动化引擎（加载规则、开始监控文件、启动定时器）
    engine.start()
    # 同步采集任务的定时计划（网页采集器）
    from app.crawler.runner import sync_schedules as sync_crawl

    sync_crawl()
    # 同步定时提醒中心的任务调度
    from app.timer.runner import sync_schedules as sync_timer

    sync_timer()
    # 启动宏录制器的监听线程（键盘鼠标监听 + 紧急停止键监听）
    from app.macro.recorder import start_listeners
    from app.macro.player import start_emergency_listener

    start_listeners()
    start_emergency_listener()

    # 让服务开始运行（yield 暂停在这里，直到服务关闭）
    yield

    # ---------- 关闭清理 ----------
    # 停止引擎（关掉文件监控、定时器），防止残留后台线程
    engine.stop()


# 创建 FastAPI 应用实例（lifespan 负责初始化/清理）
app = FastAPI(title="AutoBox 自动化工具箱", lifespan=lifespan)

# 把 API 路由挂到应用上（app/api.py 里定义的所有 /api 接口）
app.include_router(router)

# 把静态文件夹挂载为静态资源目录：
# 用统一路径工具定位（开发 = 项目根/static，打包 = exe 内资源目录）
app.mount("/static", StaticFiles(directory=str(resource_dir() / "static")), name="static")

# 把导出目录挂载为下载目录：采集器生成的 CSV 放这里
# 注意：StaticFiles 要求目录必须存在，所以挂载前先创建（幂等）
(data_dir() / "exports").mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory=str(data_dir() / "exports")), name="exports")


# ---------- 页面路由 ----------

# 首页入口：访问 http://127.0.0.1:8000/ 时返回 static/index.html
@app.get("/")
def index():
    # 读取 index.html 文件内容（encoding="utf-8" 保证中文不乱码）
    html = (resource_dir() / "static" / "index.html").read_text(encoding="utf-8")
    # 返回 HTML 响应
    from fastapi.responses import HTMLResponse

    return HTMLResponse(html)


# 各个功能模块的页面。首页的卡片跳转到这里（如 /rules.html）。
# 用白名单防止任意文件读取（安全：只允许这几个页面，别的 404）。
PAGES = ["rules", "crawler", "batch", "timer", "macro"]


@app.get("/{page}.html")
def page(page: str):
    """访问模块页面，如 /rules.html → 显示 rules.html。

    注意：模块页面必须注册路由，否则前端跳转过来会 404
    （这是之前漏掉的路由，导致点进模块显示 "Not Found"）。
    """
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse

    # 白名单校验：只允许这 5 个页面（防路径穿越等安全问题）
    if page not in PAGES:
        raise HTTPException(status_code=404, detail="页面不存在")
    # 读取对应 HTML 文件内容返回
    html = (resource_dir() / "static" / f"{page}.html").read_text(encoding="utf-8")
    return HTMLResponse(html)
