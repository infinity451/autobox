# -*- coding: utf-8 -*-
"""程序入口：启动整个 AutoBox。

运行方式（开发模式，在项目根目录）：
    python main.py

运行方式（打包模式）：
    双击 AutoBox.exe（见 build.bat 打包说明）

启动后会自动打开浏览器 http://127.0.0.1:8000。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 os：读取环境变量（控制是否自动打开浏览器，测试时用）
import os
# 导入 threading：开一个后台线程延迟打开浏览器（等服务起来再开）
import threading
# 导入 webbrowser：调用系统默认浏览器打开网页
import webbrowser
# 导入 contextlib 的 asynccontextmanager：实现"启动时初始化 / 关闭时清理"的钩子
from contextlib import asynccontextmanager

# 导入 FastAPI 框架核心类：
# FastAPI 是网页框架（提供接口服务），StaticFiles 用来托管静态文件（HTML/CSS/JS）
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
# 导入 uvicorn：把 FastAPI 应用跑起来的服务器（就像“发动机点火器”）
import uvicorn

# 导入本项目模块：
# init_db：建表；engine：全局引擎单例；router：API 路由
from app.database import init_db
from app.engine.scheduler import engine
from app.api import router
# 导入统一路径工具（打包/开发两种模式都正确）
from app.paths import data_dir, resource_dir

# ---------- 生命周期管理（优雅退出） ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理。

    这是 FastAPI 官方推荐的生命周期写法：
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


# 创建 FastAPI 应用实例（title 是文档页显示的名字；lifespan 负责初始化/清理）
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


# 编写一个简单的首页入口：
# 访问 http://127.0.0.1:8000/ 时，直接返回 static/index.html 文件内容
@app.get("/")
def index():
    # 读取 index.html 文件内容（encoding="utf-8" 保证中文不乱码）
    html = (resource_dir() / "static" / "index.html").read_text(encoding="utf-8")
    # 返回给浏览器；media_type 告诉浏览器这是 HTML 页面
    from fastapi.responses import HTMLResponse

    return HTMLResponse(html)


def main() -> None:
    """程序启动函数。"""
    # 自动打开浏览器（2 秒后等服务起来了再开）
    # 环境变量 AUTOBOX_NO_BROWSER=1 时跳过（自动化测试用，避免弹浏览器）
    if os.environ.get("AUTOBOX_NO_BROWSER") != "1":
        # Timer 开一个延迟线程：2 秒后调用 webbrowser.open 打开首页
        threading.Timer(2.0, lambda: webbrowser.open("http://127.0.0.1:8000")).start()

    # 启动网页服务器
    # host="127.0.0.1" 只在本机开放（局域网其他人暂时访问不了，安全）
    # port=8000 网页端口；访问 http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)


# 这个条件的意思是：只有“直接运行本文件”时才执行 main()
# （被别的文件 import 时不执行，避免误启动服务器）
if __name__ == "__main__":
    main()
