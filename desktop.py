# -*- coding: utf-8 -*-
"""AutoBox 桌面软件入口（唯一入口）。

双击 exe / 运行本文件 → 弹出 AutoBox 原生窗口（桌面软件形态）。

功能特性：
- 原生窗口：pywebview 加载本地界面（不弹浏览器，没有控制台黑窗）
- 单实例保护：重复启动会提示"已在运行"并退出（防止两个软件抢端口）
- 日志落盘：运行日志写入 data/autobox.log（没有控制台也能排查问题）
- 关窗即退出：关闭窗口 → 优雅停止服务 → 进程干净退出
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 sys：进程退出、判断打包环境
import sys
# 导入 threading：后台线程跑网页服务（窗口和服务器互不阻塞）
import threading
# 导入 logging：把运行日志写进文件（无控制台窗口时排查问题用）
import logging

# 导入 webview：pywebview 库，创建原生窗口
import webview
# 导入 uvicorn 的 Config 和 Server：手动控制服务器的启动/停止
from uvicorn import Config, Server

# 导入 FastAPI 应用（app/webapp.py 创建，包含全部接口和生命周期管理）
from app.webapp import app
# 导入统一路径工具（数据目录在开发/打包两种模式下都正确）
from app.paths import data_dir

# 网页服务端口（固定 8000；单实例检查也会用它判断"是否已在运行"）
PORT = 8000
# 网页地址（窗口加载的就是这个）
URL = f"http://127.0.0.1:{PORT}"


def setup_logging() -> None:
    """把运行日志写入文件（data/autobox.log）。

    为什么需要：打包成"无控制台"的软件后，print 和报错用户看不到，
    写进文件才能排查问题（比如启动失败、规则报错）。
    """
    # 确保数据目录存在
    data_dir().mkdir(parents=True, exist_ok=True)
    # 配置根日志器：所有日志（包括 uvicorn 的）都会写进这个文件
    logging.basicConfig(
        filename=str(data_dir() / "autobox.log"),  # 日志文件路径
        level=logging.INFO,                        # 记录 info 及以上级别
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # 日志格式（时间/级别/来源/内容）
        encoding="utf-8",                          # 中文不乱码
    )
    # 打印一行到日志（方便确认启动时间）
    logging.info("AutoBox 启动中...")


def check_single_instance() -> bool:
    """检查是否已经有 AutoBox 在运行（单实例保护）。

    原理：尝试占用 8000 端口。
    - 能占用 = 没有其他实例在跑，继续启动
    - 占用失败 = 端口被占（可能是另一个 AutoBox），提示并退出

    返回：True = 可以继续启动；False = 已有实例在跑，应退出
    """
    # 导入 socket：网络端口操作
    import socket

    # 创建 TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 尝试绑定 8000 端口；绑定成功说明端口空闲（没有其他实例）
        s.bind(("127.0.0.1", PORT))
        return True
    except OSError:
        # 绑定失败 = 端口被占用 = 另一个 AutoBox 正在运行
        # 弹窗提示用户（用 Windows API，不需要额外依赖）
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0, "AutoBox 已经在运行中，请先关闭它。", "AutoBox", 0x40
        )
        return False
    finally:
        # 无论成功失败都关闭这个临时 socket（释放端口）
        s.close()


def main() -> None:
    """桌面软件入口。"""
    # 第一步：配置日志（写文件）
    setup_logging()

    # 第二步：单实例检查（重复启动直接退出）
    if not check_single_instance():
        sys.exit(0)

    # 第三步：创建 uvicorn 服务器对象
    # log_config=None 表示"不配置自己的日志"，沿用我们上面配的文件日志
    server = Server(Config(app, host="127.0.0.1", port=PORT, log_level="warning", log_config=None))

    # 注意：uvicorn 默认会安装"系统信号处理器"，但 Windows 只允许主线程
    # 处理信号，在子线程里会报错。我们不需要信号处理（退出由关窗控制），
    # 所以把它替换成空操作。
    server.install_signal_handlers = lambda loop: None

    # 第四步：后台线程启动服务器
    def run_server():
        try:
            logging.info(f"网页服务启动中: {URL}")
            # 运行服务器（阻塞直到窗口关闭触发 should_exit）
            server.run()
            logging.info("网页服务已停止")
        except Exception:
            # 任何异常都记入日志（无控制台窗口时这是唯一的排查途径）
            logging.exception("网页服务异常退出")

    # daemon=True 守护线程：窗口退出时服务线程随之结束
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    # 第五步：等服务就绪再开窗口（避免窗口打开时页面还在加载）
    import socket
    import time

    ready = False
    for _ in range(50):  # 最多等 10 秒（每次 0.2 秒）
        try:
            # 尝试连接 8000 端口；连上说明服务起来了
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.2)
    if not ready:
        logging.warning("等待服务就绪超时，窗口可能显示连接失败")

    # 第六步：创建原生窗口（加载本地界面）
    window = webview.create_window(
        "AutoBox 自动化工具箱",   # 窗口标题
        URL,                       # 加载的网址（本地服务）
        width=1100,                # 窗口宽度
        height=750,                # 窗口高度
        min_size=(900, 600),       # 最小尺寸
    )

    # 绑定"窗口关闭"事件：用户点关闭按钮时，优雅停止网页服务
    # 注意：pywebview 的 start(func) 参数是"窗口显示后执行"，不是关闭回调！
    # 关闭回调要用 window.events.closing（关闭前触发）
    def on_closing():
        # 通知 uvicorn 优雅退出（触发 lifespan 清理：停引擎/监控/定时器）
        server.should_exit = True
        logging.info("窗口关闭，正在停止服务")

    window.events.closing += on_closing

    # 第七步：进入窗口事件循环（阻塞，直到用户关闭窗口）
    webview.start()

    # 窗口关闭后：等待服务线程收尾（最多等 3 秒）
    thread.join(timeout=3)
    logging.info("AutoBox 已退出")


# 只有直接运行本文件时才启动（被 import 时不执行）
if __name__ == "__main__":
    main()
