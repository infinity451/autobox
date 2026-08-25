# -*- coding: utf-8 -*-
"""触发器：负责“盯”着外部世界，一有动静就通知规则引擎。

触发器分两种：
1. 文件触发器：用 watchdog 库监控文件夹，有新文件出现/被修改时触发
2. 定时触发器：用 APScheduler 库，到点触发（比如每周五 17:00）

watchdog 的工作方式（理解即可）：
- 它会在后台开一个“监视线程”，操作系统一有文件事件，就调用我们注册的回调函数
- 回调函数 = 我们告诉它“出了这种事就打电话叫这个人”：call_back
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 watchdog 的两个类：
# Observer = “监视员”，负责启动/停止后台监视线程
# FileSystemEventHandler = “事件处理器基类”，我们继承它并改写想要响应的事件
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# ---------- 文件监控 ----------

# 记录每个监控目录对应的 Observer（监视员）对象
# 键：目录路径字符串，值：Observer 对象
# 用途：同一个目录不用重复开监视线程；停止监视时能找到对应的监视员
_observers: dict[str, Observer] = {}


class _FileHandler(FileSystemEventHandler):
    """文件事件处理器：watchdog 发现文件变动时会调用这里的方法。

    我们继承 FileSystemEventHandler，然后改写 on_created（文件出现时）
    和 on_modified（文件被修改时）两个方法。
    """

    # __init__ 是 Python 类的“构造方法”：创建这个处理器时自动调用
    # 参数 callback 是我们定义的“回调函数”，事件发生时调用它来通知引擎
    def __init__(self, callback):
        # super().__init__() 先执行父类的初始化（固定写法，保持父类行为）
        super().__init__()
        # 把回调函数存起来，后面事件发生时用它
        self._callback = callback

    def on_created(self, event):
        """文件/文件夹被创建时触发。"""
        # event.is_directory 是 True 表示这是新建了一个文件夹，我们不关心文件夹，只看文件
        if not event.is_directory:
            # event.src_path 是出事的文件路径；调回调函数，第二个参数标事件类型为 added（新增）
            self._callback(str(event.src_path), "added")

    def on_modified(self, event):
        """文件被修改时触发。"""
        # 同样忽略文件夹
        if not event.is_directory:
            # 回调通知引擎，事件类型为 modified（修改）
            self._callback(str(event.src_path), "modified")


def watch_dir(path: str, callback) -> None:
    """开始监控一个目录。

    参数：
        path: 要监控的目录路径（如 "D:/下载"）
        callback: 回调函数，签名 callback(文件路径, 事件类型)
    """
    # 如果这个目录已经在监控中，就不重复监控（直接返回）
    if path in _observers:
        return
    # 创建一个 Observer（监视员），并设置：
    # - 事件处理器：_FileHandler(callback)（出事就调 callback）
    # - 监控路径：path
    # - recursive=False 表示只监控这一层，不监控子文件夹（避免触发太频繁）
    observer = Observer()
    observer.schedule(_FileHandler(callback), path, recursive=False)
    # 启动监视线程（start 后 watchdog 在后台一直盯着）
    observer.start()
    # 把监视员登记进字典，方便以后管理
    _observers[path] = observer


def unwatch_dir(path: str) -> None:
    """停止监控一个目录（比如规则被删了，就没必要再盯着）。"""
    # 从字典里取监视员；取不到说明没在监控，直接返回
    observer = _observers.pop(path, None)
    # 存在才需要停止
    if observer:
        # 停止监视线程
        observer.stop()
        # join 表示等线程完全退出后再继续（干净利落地收尾）
        observer.join(timeout=5)


def unwatch_all() -> None:
    """停止所有文件监控（程序退出时调用，防止残留后台线程）。"""
    # 遍历字典里的所有目录，逐个停止监控
    for path in list(_observers.keys()):
        # 调用上面的 unwatch_dir 停止单个目录的监控
        unwatch_dir(path)


# ---------- 定时触发 ----------

# 导入 APScheduler 的 BackgroundScheduler：后台调度器，可以安排“到点执行函数”
# 它自己开一个后台线程，到时间就调用我们注册的函数
from apscheduler.schedulers.background import BackgroundScheduler
# 导入 CronTrigger：把 "0 17 * * 5" 这种 cron 字符串解析成“具体什么时候执行”
# cron 格式：分 时 日 月 周，如 "0 17 * * 5" = 每周五 17:00
from apscheduler.triggers.cron import CronTrigger

# 全局调度器对象（整个程序共用一个）
_scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    """启动定时调度器（只在程序启动时调用一次）。"""
    # running 属性判断调度器是否已在运行；防止重复启动
    if not _scheduler.running:
        # 启动调度器的后台线程
        _scheduler.start()


def stop_scheduler() -> None:
    """停止定时调度器（程序退出时调用）。"""
    # 正在运行才需要停止
    if _scheduler.running:
        # 停止并等线程退出
        _scheduler.shutdown(wait=False)


def add_cron_job(func, job_id: str, cron: str) -> None:
    """注册一个定时任务：到 cron 指定的时间，调用 func。

    参数：
        func:   到点要执行的函数（无参数）
        job_id: 任务唯一编号（用规则 id，方便以后取消/更新）
        cron:   cron 表达式，如 "0 17 * * 5"（每周五 17:00）
    """
    # add_job 是 APScheduler 的注册方法：
    # - func 是要执行的函数
    # - CronTrigger.from_crontab(cron) 解析 cron 字符串成“时间计划”
    # - id=job_id 给任务起名，replace_existing=True 表示如果同名任务已存在就替换
    _scheduler.add_job(func, CronTrigger.from_crontab(cron), id=job_id, replace_existing=True)


def remove_job(job_id: str) -> None:
    """删除一个定时任务（规则被删/被暂停时调用）。"""
    # get_job 找不到就返回 None；存在才删除
    if _scheduler.get_job(job_id):
        # remove_job 删除任务
        _scheduler.remove_job(job_id)
