# -*- coding: utf-8 -*-
"""SQLite 数据层：所有模块共享一个数据库文件。

这里封装了“读写数据库”的所有基础操作。
你不需要懂 SQLite 的细节，只要知道：
- 数据库是一个文件（data/autobox.db），就像一张大表格存所有数据
- 本文件提供 4 个函数：init_db（建表）、query（查数据）、execute（改数据）、log（记日志）
"""

# from __future__ import annotations 是 Python 的“允许提前使用类型注解”开关
# 它让代码里可以写 list[str] 这种新式类型写法（老版本 Python 会报错），方便阅读
from __future__ import annotations

# 导入 sqlite3 模块：Python 自带的“轻量级数据库”，不需要额外安装，用来存储规则等数据
import sqlite3
# 导入 threading 模块：提供“线程锁”。我们的程序后面会多线程运行（监控文件的同时处理网页请求），
# 多个线程同时写数据库会互相干扰，用锁保证同一时刻只有一个线程在写
import threading
# 导入 Path：用来处理文件路径（跨系统兼容的路径写法，比如 Windows 的 D:\ 和 Linux 的 / 都能处理）
from pathlib import Path

# 计算数据库文件的完整路径：
# __file__ 是“本文件（database.py）的路径”，parent 是它的上级目录（app/），
# 再 parent 就是项目根目录（autobox/），最后拼上 data/autobox.db
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "autobox.db"

# 创建一个线程锁对象（线程锁 = 一把“门锁”，进门前拿锁，出来还锁，防止两人同时进门）
# 后面所有写数据库的地方都会先拿这把锁
_lock = threading.Lock()


def get_conn() -> sqlite3.Connection:
    """获取一个数据库连接。

    连接（Connection）就像一条“通往数据库的管道”，所有读写都要通过它。
    注意：SQLite 的连接不能跨线程共用，所以每次要用时都新建一个。
    """
    # mkdir 创建数据目录；parents=True 表示“如果上级目录也没有，就一起建”
    # exist_ok=True 表示“目录已经存在也没关系，不报错”
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 打开数据库文件，返回连接对象
    # check_same_thread=False 表示“允许这个连接被不同线程使用”（我们简单起见这样设置）
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # row_factory = sqlite3.Row 意思是：查询结果用“按列名取值”的方式返回
    # 默认返回的是元组（只能靠下标 row[0] 取），改成 Row 后可以用 row["name"] 取，更直观
    conn.row_factory = sqlite3.Row
    # 把连接返回给调用者
    return conn


def init_db() -> None:
    """初始化数据库：建好所有需要的表格（如果还不存在的话）。

    “幂等”的意思：运行多少次效果都一样，不会重复建表报错。
    程序启动时调用一次即可。
    """
    # with _lock: 先拿锁，执行完自动还锁（with 语法保证无论成功失败都会释放）
    # with get_conn() as conn: 打开连接，执行完自动关闭
    with _lock, get_conn() as conn:
        # executescript 可以一次执行多句 SQL（以分号分隔）
        # IF NOT EXISTS = “如果表不存在才创建”，防止重复创建报错
        conn.executescript(
            """
            -- 规则表：保存用户创建的每一条“如果…就…”规则
            CREATE TABLE IF NOT EXISTS rules (
                id          TEXT PRIMARY KEY,    -- 规则唯一编号（主键，不能重复）
                name        TEXT NOT NULL,       -- 规则名字（如“视频自动归档”）
                enabled     INTEGER NOT NULL DEFAULT 1,  -- 是否启用：1=启用，0=暂停
                trigger     TEXT NOT NULL,       -- 触发器配置（JSON 文本，如“监控哪个文件夹”）
                conditions  TEXT NOT NULL DEFAULT '[]',  -- 条件列表（JSON 文本，如“文件名含‘视频’”）
                actions     TEXT NOT NULL DEFAULT '[]',  -- 动作列表（JSON 文本，如“移动到 D:\\视频”）
                created_at  TEXT NOT NULL,       -- 创建时间
                updated_at  TEXT NOT NULL        -- 最后修改时间
            );

            -- 运行日志表：记录每条规则每次触发的执行结果
            CREATE TABLE IF NOT EXISTS run_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增编号
                rule_id    TEXT,                -- 哪条规则触发的（对不上规则名也能查）
                rule_name  TEXT,                -- 规则名字（日志里直接显示）
                level      TEXT NOT NULL DEFAULT 'info',  -- 日志级别：info/success/warn/error
                message    TEXT NOT NULL,       -- 日志内容（如“已移动 3 个文件”）
                created_at TEXT NOT NULL        -- 日志时间
            );

            -- 设置表：存一些零散配置（key-value 键值对形式）
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,         -- 配置项名字
                value TEXT                      -- 配置项内容
            );

            -- 采集任务表（网页采集器模块）：保存每条采集配置
            CREATE TABLE IF NOT EXISTS crawler_tasks (
                id             TEXT PRIMARY KEY,    -- 任务唯一编号
                name           TEXT NOT NULL,       -- 任务名字（如“新闻标题采集”）
                url            TEXT NOT NULL,       -- 要采集的网页地址
                item_selector  TEXT NOT NULL,       -- 列表容器选择器（每条记录的外壳）
                fields         TEXT NOT NULL DEFAULT '[]',  -- 字段配置（JSON 文本）
                cron           TEXT NOT NULL DEFAULT '',     -- 定时表达式（空=不自动采集）
                max_items      INTEGER NOT NULL DEFAULT 50,  -- 最多采集多少条
                enabled        INTEGER NOT NULL DEFAULT 1,   -- 是否启用
                created_at     TEXT NOT NULL,       -- 创建时间
                updated_at     TEXT NOT NULL        -- 更新时间
            );

            -- 采集运行记录表：每次执行采集的结果
            CREATE TABLE IF NOT EXISTS crawl_runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增编号
                task_id    TEXT,                -- 哪个任务跑的
                task_name  TEXT,                -- 任务名字（日志显示用）
                status     TEXT NOT NULL,       -- 结果：success / error
                item_count INTEGER NOT NULL DEFAULT 0,  -- 采集到多少条
                csv_file   TEXT,                -- 导出的 CSV 文件名（出错时为空）
                message    TEXT,                -- 说明（出错时是错误信息）
                created_at TEXT NOT NULL        -- 运行时间
            );

            -- 定时任务表（定时提醒中心模块）：保存到点要做什么
            CREATE TABLE IF NOT EXISTS timer_tasks (
                id         TEXT PRIMARY KEY,    -- 任务唯一编号
                name       TEXT NOT NULL,       -- 任务名字（如“喝水提醒”）
                action     TEXT NOT NULL,       -- 动作：notify/shutdown/restart/sleep/open
                cron       TEXT NOT NULL,       -- 定时表达式（如 0 9 * * * = 每天 9 点）
                message    TEXT NOT NULL DEFAULT '',   -- 提醒内容（提醒类用）
                program    TEXT NOT NULL DEFAULT '',   -- 程序路径（打开程序类用）
                enabled    INTEGER NOT NULL DEFAULT 1,  -- 是否启用
                created_at TEXT NOT NULL,       -- 创建时间
                updated_at TEXT NOT NULL        -- 更新时间
            );
            """
        )


def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """查询数据：执行 SELECT 语句，返回所有结果行。

    参数：
        sql: SQL 语句，如 "SELECT * FROM rules"
        params: 传给 SQL 的参数，如 (rule_id,)
            用参数而不是直接拼字符串，可以防止“SQL 注入”攻击（安全习惯）
    返回：
        行对象列表，每行可以用 row["列名"] 取值
    """
    # with get_conn() as conn: 自动打开连接、用完自动关闭
    with get_conn() as conn:
        # 执行查询并返回所有结果（fetchall = 取全部行）
        return conn.execute(sql, params).fetchall()


def execute(sql: str, params: tuple = ()) -> int:
    """执行写操作：INSERT（插入）/ UPDATE（修改）/ DELETE（删除）。

    返回：
        最后插入行的编号（lastrowid），一般用不上，但保留返回以便调试
    """
    # 写操作必须加锁：防止多线程同时改数据造成错乱
    with _lock, get_conn() as conn:
        # 执行 SQL 语句
        cur = conn.execute(sql, params)
        # commit = “正式保存”。SQLite 默认不自动保存，必须 commit 才真正写入文件
        conn.commit()
        # 返回最后插入的行的 id（没有插入则返回 0）
        return cur.lastrowid or 0


def log(rule_id: str | None, rule_name: str, level: str, message: str) -> None:
    """往日志表里写一条日志。

    参数：
        rule_id:   触发这条日志的规则 id（没有就是 None）
        rule_name: 规则名字（方便人看）
        level:     级别：info（提示）/ success（成功）/ warn（警告）/ error（错误）
        message:   日志正文
    """
    # 在函数内部导入 datetime：只有用到时才加载，让程序启动更快
    from datetime import datetime

    # 调用上面的 execute 函数，插入一条日志
    # isoformat(timespec="seconds") 把当前时间转成字符串，精确到秒，如 "2026-08-25T10:30:00"
    execute(
        "INSERT INTO run_logs (rule_id, rule_name, level, message, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (rule_id, rule_name, level, message, datetime.now().isoformat(timespec="seconds")),
    )
