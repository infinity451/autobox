# -*- coding: utf-8 -*-
"""引擎主控：把触发器、规则、条件匹配、动作执行串成一条完整链路。

工作流程（以“文件出现”为例）：
1. 用户在网页上创建了一条规则（存进数据库）
2. 引擎启动时，把所有“启用”的规则加载进内存，并注册对应的触发器
3. 下载文件夹出现新文件 → watchdog 通知引擎（handle_file_event）
4. 引擎找出“监控目录匹配”且“条件满足”的规则
5. 按顺序执行规则的动作（移动/复制/通知…），并写入运行日志
6. 网页上能看到这条规则的执行历史

防死循环（重点设计）：
“移动文件”这个动作本身也会触发 watchdog 的“文件出现”事件，
如果不加防护，会出现：移动文件 → 触发规则 → 又移动 → 无限循环。
解决方案：引擎把“自己刚操作过的文件路径”记下来（带时间戳），
watchdog 再次报告这个路径时，发现是“自己干的”，就忽略。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 time：用来记“操作时间戳”，配合防死循环
import time

# 导入数据库模块（读规则、写日志）
from .. import database
# 导入规则管理函数（list_rules 读所有规则）
from .rules import list_rules
# 导入条件匹配函数
from .matcher import extract_file_info, match_conditions
# 导入动作执行函数
from .actions import run_actions
# 导入触发器函数（注册/停止文件监控、定时任务）
from . import triggers
# 导入规则模型的触发器类型常量（判断规则是文件类还是定时类）
from ..models import TRIGGER_FILE_ADDED, TRIGGER_FILE_MODIFIED, TRIGGER_SCHEDULE


class Engine:
    """自动化引擎：整个项目的心脏。"""

    def __init__(self):
        # 规则缓存：所有“启用”的规则，加载到内存里加快查找（不用每次查数据库）
        self.rules: list[dict] = []
        # 防死循环记录：{文件路径: 时间戳}，记录引擎自己刚动过的文件
        self._busy: dict[str, float] = {}
        # 已监控的目录集合（增量同步用，见 _sync_watches）
        self._watched_dirs: set[str] = set()
        # 已注册的定时任务：{规则id: cron表达式}（增量同步用，见 _sync_schedule_rules）
        self._scheduled_rules: dict[str, str] = {}
        # 防死循环记录的最长保留时间（秒）：超过这个时间的条目会被清理
        self._busy_ttl = 30
        # 引擎是否已启动
        self._started = False

    # ---------- 生命周期 ----------

    def start(self) -> None:
        """启动引擎：加载规则 + 注册所有触发器。"""
        # 标记已启动
        self._started = True
        # 加载启用中的规则
        self.reload_rules()
        # 启动定时调度器（APScheduler 的后台线程）
        triggers.start_scheduler()
        # 注册所有文件监控和定时任务
        self._register_all()
        # 写一条启动日志（方便排查）
        database.log(None, "引擎", "info", "AutoBox 引擎已启动")

    def stop(self) -> None:
        """停止引擎：关掉所有监控和定时器。"""
        # 标记已停止
        self._started = False
        # 停止所有文件监控
        triggers.unwatch_all()
        # 停止定时调度器
        triggers.stop_scheduler()
        # 清空增量同步的记录（下次启动重新全量注册）
        self._watched_dirs = set()
        self._scheduled_rules = {}
        # 写一条停止日志
        database.log(None, "引擎", "info", "AutoBox 引擎已停止")

    def reload_rules(self) -> None:
        """从数据库重新加载规则缓存（只加载启用的）。"""
        # list_rules() 返回所有规则，这里只保留 enabled=True 的
        # enabled 是布尔值 True/False，直接用 if 判断
        self.rules = [r for r in list_rules() if r["enabled"]]

    def refresh(self) -> None:
        """刷新：规则被增/删/改/暂停后调用，让引擎立即按最新规则工作。

        优化说明（优化清单 #3）：以前是全量重建（停掉所有监控 + 删掉所有
        定时任务再重注册），规则一多会有抖动，而且会把采集器/定时中心的
        定时任务误删。现在改成增量同步：只处理变化的部分，没变的目录和
        任务完全不动。
        """
        # 重新加载规则缓存
        self.reload_rules()
        # 增量同步文件监控（只增删变化的目录）
        self._sync_watches()
        # 增量同步定时任务（只增删变化的任务）
        self._sync_schedule_rules()

    # ---------- 注册触发器 ----------

    def _register_all(self) -> None:
        """全量注册（只在引擎启动时调用一次）。

        启动时没有历史状态，全量注册一次最干净。
        """
        # 清空已记录的状态（从零开始）
        self._watched_dirs = set()
        self._scheduled_rules = {}
        # 先停掉所有文件监控（清场）
        triggers.unwatch_all()
        # 再按最新规则注册（复用增量同步函数）
        self._sync_watches()
        self._sync_schedule_rules()

    def _sync_watches(self) -> None:
        """增量同步文件监控：只新增/移除变化的目录，没变的目录不动。

        对比"当前需要的目录"和"已监控的目录"两个集合：
        - 需要但没在监控的 → 新增监控
        - 在监控但不再需要的 → 停止监控
        """
        # 计算当前需要的监控目录（规范化后去重，防止正反斜杠重复）
        needed: set[str] = set()
        for rule in self.rules:
            # 取出规则的触发器类型
            ttype = rule["trigger"].get("type")
            # 文件类触发器：监控目录加进"需要"集合
            if ttype in (TRIGGER_FILE_ADDED, TRIGGER_FILE_MODIFIED):
                needed.add(self._norm_path(rule["trigger"].get("watch_dir", "")))

        # 移除"不再需要"的目录：已监控的 - 需要的 = 要停的
        for d in list(self._watched_dirs - needed):
            # 停止对这个目录的监控
            triggers.unwatch_dir(d)
            # 从已监控集合移除
            self._watched_dirs.discard(d)

        # 新增"需要但没监控"的目录：需要的 - 已监控的 = 要加的
        for d in needed - self._watched_dirs:
            # 注册文件监控（回调指向 handle_file_event）
            triggers.watch_dir(d, self.handle_file_event)
            # 加入已监控集合
            self._watched_dirs.add(d)

    def _sync_schedule_rules(self) -> None:
        """增量同步定时任务：只处理新增/删除/变化的任务。

        注意：规则引擎的定时任务用"规则 id"做任务名，与采集器（crawl_ 前缀）
        和定时中心（timer_ 前缀）互不干扰——这里绝不碰别人的任务。
        """
        # 计算当前需要的定时任务：{规则id: cron表达式}
        needed: dict[str, str] = {}
        for rule in self.rules:
            # 定时触发器：记录它的 cron
            if rule["trigger"].get("type") == TRIGGER_SCHEDULE:
                needed[rule["id"]] = rule["trigger"].get("cron", "")

        # 移除"不再需要"的任务：规则被删了/改成文件类型了
        for rid in list(self._scheduled_rules):
            if rid not in needed:
                # 删除定时任务
                triggers.remove_job(rid)
                # 从记录移除
                del self._scheduled_rules[rid]

        # 新增或更新：add_cron_job 的 replace_existing=True 会自动覆盖同名任务，
        # 所以 cron 变了直接重新注册即可（不用先删再建）
        for rid, cron in needed.items():
            # 注册/更新定时任务（到点执行 handle_schedule，参数是规则 id）
            triggers.add_cron_job(
                lambda r=rid: self.handle_schedule(r),
                job_id=rid,
                cron=cron,
            )
            # 记录已注册（连同最新 cron）
            self._scheduled_rules[rid] = cron

    # ---------- 事件处理 ----------

    @staticmethod
    def _norm_path(p: str) -> str:
        """规范化路径：统一成“正斜杠 + 小写”。

        为什么要规范化：Windows 上同一个目录可能有两种写法：
            D:/下载  （正斜杠）
            D:\\下载  （反斜杠）
        watchdog 返回的路径是反斜杠，用户填的可能是正斜杠，
        直接比较字符串永远不相等，所以先统一格式再比较。
        """
        from pathlib import Path

        # 空路径直接返回空字符串（避免报错）
        if not p:
            return ""
        # 转成 Path 对象再转回字符串（统一分隔符），反斜杠替换成正斜杠，全部转小写
        return str(Path(p)).replace("\\", "/").lower()

    def _is_busy(self, path: str) -> bool:
        """判断一个路径是否“刚被本引擎操作过”（防死循环检查）。

        如果路径在 _busy 记录里，并且是 2 秒内操作的，就认为是“自己干的”，忽略。
        """
        # 从记录里取该路径的时间戳；取不到返回 0（很早以前=不算忙）
        ts = self._busy.get(path, 0)
        # 当前时间 - 记录时间 <= 2 秒，说明刚操作过
        return (time.time() - ts) <= 2

    def _mark_busy(self, path: str) -> None:
        """把路径记进“刚操作过”清单（执行动作前调用）。

        顺带清理过期条目：超过 _busy_ttl（30 秒）的旧记录删掉，
        防止字典无限增长（这是优化清单 #2：_busy 只增不减的内存隐患）。
        """
        # 记录当前时间戳（秒）
        self._busy[path] = time.time()
        # 清理过期条目：遍历时修改字典，必须用 list() 拷贝一份再遍历
        # 时间戳早于"当前时间 - 30 秒"的都删掉（防死循环只需记住最近 30 秒）
        cutoff = time.time() - self._busy_ttl
        for p, ts in list(self._busy.items()):
            # 这条记录太旧了，删掉（不再需要）
            if ts < cutoff:
                del self._busy[p]

    def handle_file_event(self, path: str, event_type: str) -> None:
        """文件事件入口：下载文件夹有新文件/文件被修改时被调用。

        参数：
            path: 出事的文件完整路径
            event_type: "added"（新增）或 "modified"（修改）
        """
        # 防死循环第一道闸：如果这个路径是引擎自己刚操作的，直接忽略
        if self._is_busy(path):
            return
        # 用 pathlib 拿路径的父目录（即文件所在的文件夹），
        # 后面用它匹配“哪条规则的监控目录就是这里”
        from pathlib import Path

        parent_dir = str(Path(path).parent)
        # 规范化目录路径（见 _norm_path 说明）
        parent_dir_norm = self._norm_path(parent_dir)

        # 遍历所有启用规则，找匹配的
        for rule in self.rules:
            # 取出规则的触发器
            t = rule["trigger"]
            # 只处理文件类触发器（定时规则不在这里处理）
            if t.get("type") not in (TRIGGER_FILE_ADDED, TRIGGER_FILE_MODIFIED):
                continue
            # 规则监控的目录必须等于文件所在目录（不是这个目录的事就不管）
            # 两边都规范化再比较，避免 Windows 正斜杠/反斜杠不一致导致匹配失败
            if self._norm_path(t.get("watch_dir", "")) != parent_dir_norm:
                continue
            # 事件类型必须匹配：规则说“新增才触发”，那修改事件就不触发
            if t.get("type") == TRIGGER_FILE_ADDED and event_type != "added":
                continue
            if t.get("type") == TRIGGER_FILE_MODIFIED and event_type != "modified":
                continue
            # 走到这里说明“触发条件满足”，交给 _execute_rule 执行
            self._execute_rule(rule, path)

    def handle_schedule(self, rule_id: str) -> None:
        """定时任务入口：到点了被调度器调用。"""
        # 从规则缓存里找这条规则（id 匹配）
        rule = next((r for r in self.rules if r["id"] == rule_id), None)
        # 找不到（比如规则被删了）就不处理
        if rule is None:
            return
        # 定时触发没有具体文件，info 用空字典，watch_dir 用规则里配置的（可能为空字符串）
        # 典型场景：定时提醒（notify 动作），file 相关动作会因缺少路径而记录错误日志
        self._execute_rule(rule, None)

    def _execute_rule(self, rule: dict, path: str | None) -> None:
        """执行一条规则：提取文件信息 → 条件匹配 → 执行动作 → 写日志。

        参数：
            rule: 规则字典
            path: 触发的文件路径；定时规则时为 None
        """
        # 规则名字（日志里要显示）
        name = rule["name"]
        # 规则 id
        rid = rule["id"]
        # 监控目录（文件类规则有，定时规则可能没有，用空字符串兜底）
        watch_dir = rule["trigger"].get("watch_dir", "")

        # 文件信息字典：有具体文件就提取，没有（定时规则）就用空字典
        info = extract_file_info(path) if path else {}

        # 条件匹配：不满足条件的规则不执行（match_conditions 返回 True 表示满足）
        if not match_conditions(rule["conditions"], info):
            return

        # 防死循环第二道闸：有具体文件时，先把路径记入“刚操作过”
        if path:
            self._mark_busy(path)

        # 执行所有动作；用 try/except 包起来：
        # 任何一步出错（比如目录写不了、文件被占用）都不能让引擎崩溃，而是记错误日志
        try:
            # run_actions 返回每个动作的结果列表
            results = run_actions(rule, info, watch_dir)
            # 把每个动作结果写进运行日志（rule_id、规则名、级别、内容）
            for r in results:
                # 动作成功记 success 级别，失败记 error 级别
                database.log(rid, name, "success" if r["ok"] else "error", f"[{r['type']}] {r['message']}")
        except Exception as e:  # noqa: BLE001
            # 出了任何异常：记 error 日志，让用户能在网页日志里看到原因
            database.log(rid, name, "error", f"规则执行出错: {e}")


# ---------- 全局单例 ----------
# 整个程序共用一个引擎实例（单例模式）：
# 所有地方都通过 engine.start() / engine.refresh() 使用它，
# 保证只有一套监控、一套定时器，不会乱
engine = Engine()
