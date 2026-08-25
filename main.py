# -*- coding: utf-8 -*-
"""程序入口：启动整个 AutoBox。

运行方式（在项目根目录）：
    python main.py

启动后：
1. 初始化数据库（建表）
2. 启动自动化引擎（加载规则、开始监控）
3. 启动网页服务：浏览器打开 http://127.0.0.1:8000 即可使用
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

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

# 创建 FastAPI 应用实例（title 是文档页显示的名字）
app = FastAPI(title="AutoBox 自动化工具箱")

# 把 API 路由挂到应用上（app/api.py 里定义的所有 /api 接口）
app.include_router(router)

# 把 static 文件夹挂载为静态资源目录：
# 浏览器访问 /static/xxx 就能拿到这个文件夹里的 HTML/CSS/JS 文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 把 data/exports 挂载为导出文件目录：
# 采集器生成的 CSV 文件放这里，浏览器访问 /exports/xxx.csv 即可下载
# 注意：目录不存在时 StaticFiles 会报错，所以先创建
from pathlib import Path

Path("data/exports").mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory="data/exports"), name="exports")


# 编写一个简单的首页入口：
# 访问 http://127.0.0.1:8000/ 时，直接返回 static/index.html 文件内容
# （返回 HTML 响应，浏览器就会渲染出页面）
@app.get("/")
def index():
    # 读取 index.html 文件内容（encoding="utf-8" 保证中文不乱码）
    html = open("static/index.html", encoding="utf-8").read()
    # 返回给浏览器；media_type 告诉浏览器这是 HTML 页面
    from fastapi.responses import HTMLResponse

    return HTMLResponse(html)


def main() -> None:
    """程序启动函数。"""
    # 第一步：初始化数据库（建表；已经建过也没关系，幂等）
    init_db()
    # 第二步：启动自动化引擎（加载规则、开始监控文件、启动定时器）
    engine.start()
    # 第三步：同步采集任务的定时计划（网页采集器模块，配置了 cron 的任务开始自动采集）
    from app.crawler.runner import sync_schedules as sync_crawl

    sync_crawl()
    # 第四步：同步定时提醒中心的任务调度（定时提醒/关机/打开程序）
    from app.timer.runner import sync_schedules as sync_timer

    sync_timer()
    # 第五步：启动宏录制器的监听线程（键盘鼠标监听 + 紧急停止键监听）
    from app.macro.recorder import start_listeners
    from app.macro.player import start_emergency_listener

    start_listeners()
    start_emergency_listener()
    # 第六步：启动网页服务器
    # host="127.0.0.1" 只在本机开放（局域网其他人暂时访问不了，安全）
    # port=8000 网页端口；访问 http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)


# 这个条件的意思是：只有“直接运行本文件”时才执行 main()
# （被别的文件 import 时不执行，避免误启动服务器）
if __name__ == "__main__":
    main()
