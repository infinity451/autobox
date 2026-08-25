# -*- coding: utf-8 -*-
"""桌面模式启动器：把 AutoBox 变成真正的桌面应用（原生窗口，不弹浏览器）。

原理（一句话）：在后台线程启动本地网页服务，再用 pywebview 开一个
"原生窗口"加载这个网页——用户看到的就是一个独立的应用窗口。

效果：
- 双击 exe → 弹出 AutoBox 窗口（像微信/记事本一样）
- 关掉窗口 → 服务自动停止 → 进程退出（干净利落）
- 网页界面（5 个模块）零改动直接复用

依赖：pywebview（Windows 上用系统自带的 WebView2 引擎）
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 threading：后台线程跑网页服务（窗口和服务器互不阻塞）
import threading

# 导入 webview：pywebview 库，创建原生窗口
import webview
# 导入 uvicorn：网页服务器
import uvicorn
# 导入 uvicorn 的 Config 和 Server：
# 用它们可以手动控制服务器的启动/停止（窗口关闭时优雅退出）
from uvicorn import Config, Server

# 导入 FastAPI 应用（main.py 里创建的 app，包含所有接口和静态资源）
from main import app
# 导入引擎（窗口关闭时要优雅停止监控/定时器）
from app.engine.scheduler import engine

# 网页服务端口（固定 8000；如果被占用，后面可改成自动换端口）
PORT = 8000
# 网页地址
URL = f"http://127.0.0.1:{PORT}"


def main() -> None:
    """桌面模式入口。"""
    # 第一步：创建 uvicorn 服务器对象（Config 是配置，Server 是服务器）
    server = Server(Config(app, host="127.0.0.1", port=PORT, log_level="warning"))

    # 第二步：后台线程启动服务器
    # 注意：uvicorn 默认会在启动时安装"系统信号处理器"（Ctrl+C 等），
    # 但 Windows 只允许主线程处理信号，在子线程里会报错。
    # 我们不需要信号处理（退出由"关闭窗口"控制），所以先把它替换成空操作。
    server.install_signal_handlers = lambda loop: None

    # 定义服务线程函数：启动服务器，出错时打印异常（方便排查）
    def run_server():
        try:
            # 打印一行启动信息（控制台可见）
            print(f"[AutoBox] 网页服务启动中: {URL}", flush=True)
            # 运行服务器（阻塞直到窗口关闭触发 should_exit）
            server.run()
            # 服务退出后打印提示
            print("[AutoBox] 网页服务已停止", flush=True)
        except Exception:
            # 任何异常都打印完整堆栈（排查问题用）
            import traceback

            traceback.print_exc()

    # 启动服务线程；daemon=True 表示守护线程：窗口退出时服务线程随之结束
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # 第三步：等服务就绪再开窗口（避免窗口打开时页面还在加载）
    # 用 socket 探测端口：能连上说明服务起来了
    import socket

    ready = False
    for _ in range(50):  # 最多等 10 秒（每次 0.2 秒）
        try:
            # 尝试连接 8000 端口
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                ready = True
                break
        except OSError:
            # 还没起来，等 0.2 秒再试
            import time

            time.sleep(0.2)
    if not ready:
        # 服务没起来也继续开窗口（页面会显示连接失败，能看出来）
        print("[AutoBox] 警告: 等待服务就绪超时", flush=True)

    # 第三步：定义"窗口关闭时"的回调函数
    def on_closing():
        # 通知 uvicorn 优雅退出（会触发 lifespan 的清理逻辑，停引擎/监控/定时器）
        server.should_exit = True

    # 第四步：创建原生窗口
    # create_window(标题, 网址, 宽, 高, 最小尺寸)
    # 窗口内容 = 加载本地网页服务的首页
    window = webview.create_window(
        "AutoBox 自动化工具箱",   # 窗口标题
        URL,                       # 加载的网址（本地服务）
        width=1100,                # 窗口宽度
        height=750,                # 窗口高度
        min_size=(900, 600),       # 最小尺寸（防止窗口缩太小界面错乱）
    )

    # 绑定"窗口关闭"事件：用户点关闭按钮时，优雅停止网页服务
    # 注意：pywebview 的 start(func) 参数是"窗口显示后执行"，不是关闭回调！
    # 关闭回调要用 window.events.closing（关闭前触发）
    window.events.closing += on_closing

    # 第五步：进入窗口事件循环（阻塞在这里，直到用户关闭窗口）
    # 窗口关闭时触发 closing 事件 → on_closing 停服务 → 程序结束
    webview.start()

    # 窗口关闭后：等待服务线程收尾（最多等 3 秒，防止残留线程）
    thread.join(timeout=3)


# 只有直接运行本文件时才启动桌面模式
if __name__ == "__main__":
    main()
