# -*- coding: utf-8 -*-
"""规则数据模型：定义一条“如果…就…”规则长什么样。

这个文件不干“活”，只做两件事：
1. 用常量（大写名字）定义“规则里可以填什么”，比如触发器有哪几种类型
2. 提供校验函数，保证用户填的规则是合法的，不合法的直接拒绝

一条规则的数据结构（存在数据库里是 JSON 文本，这里用字典表示）：

{
  "id": "abc123",            # 唯一编号
  "name": "视频自动归档",     # 规则名字
  "enabled": true,           # 是否启用
  "trigger": {               # 触发器：什么时候开始干活
      "type": "file_added",  #   类型：文件出现
      "watch_dir": "D:/下载"  #   监控哪个文件夹
  },
  "conditions": [            # 条件：满足这些才执行（可留空 = 无条件）
      {"field": "ext", "op": "in", "value": [".mp4", ".mkv"]}   # 扩展名是视频格式
  ],
  "actions": [               # 动作：要做什么（按顺序执行）
      {"type": "move", "dest_dir": "D:/视频"},
      {"type": "notify", "message": "已归档 {{file.name}}"}
  ]
}
"""

# from __future__ import annotations：允许提前使用新式类型注解，方便阅读
from __future__ import annotations

# 导入 uuid：用来生成全球唯一的随机编号（规则的 id），避免两条规则 id 撞车
import uuid
# 导入 datetime：生成规则的创建/修改时间
from datetime import datetime

# ---------- 触发器类型（trigger.type 可以填的值） ----------
# 文件出现时触发（比如下载文件夹里多了个新文件）
TRIGGER_FILE_ADDED = "file_added"
# 文件被修改时触发
TRIGGER_FILE_MODIFIED = "file_modified"
# 定时触发（cron 表达式，比如每周五 17:00）
TRIGGER_SCHEDULE = "schedule"

# 所有合法的触发器类型，用来做校验（新类型以后在这里加一行就能扩展）
TRIGGER_TYPES = [TRIGGER_FILE_ADDED, TRIGGER_FILE_MODIFIED, TRIGGER_SCHEDULE]

# ---------- 条件字段（conditions[].field 可以填的值） ----------
# 文件名（如“第8课视频.mp4”的文件名部分）
FIELD_NAME = "name"
# 文件扩展名（如 .mp4）
FIELD_EXT = "ext"
# 文件大小（单位 MB）
FIELD_SIZE = "size"
# 文件路径（完整路径）
FIELD_PATH = "path"

# ---------- 条件操作符（conditions[].op 可以填的值） ----------
# 包含：文件名里包含某关键词
OP_CONTAINS = "contains"
# 等于（用于扩展名等精确匹配）
OP_EQUALS = "equals"
# 属于：值在给定列表里（如扩展名是 .mp4 或 .mkv）
OP_IN = "in"
# 大于（用于文件大小）
OP_GREATER = "gt"
# 小于
OP_LESS = "lt"

# 每个字段允许用什么操作符（做校验用：比如“大小”不能用“包含”）
# 这是一个字典：键是字段名，值是“该字段允许的操作符列表”
FIELD_ALLOWED_OPS = {
    FIELD_NAME: [OP_CONTAINS, OP_EQUALS],
    FIELD_EXT: [OP_EQUALS, OP_IN],
    FIELD_SIZE: [OP_GREATER, OP_LESS],
    FIELD_PATH: [OP_CONTAINS, OP_EQUALS],
}

# ---------- 动作类型（actions[].type 可以填的值） ----------
# 移动文件：把触发规则的那个文件移动到指定目录
ACTION_MOVE = "move"
# 复制文件
ACTION_COPY = "copy"
# 重命名文件（需要提供新文件名，可含模板变量）
ACTION_RENAME = "rename"
# 发通知（先写日志，后续版本支持弹窗）
ACTION_NOTIFY = "notify"

# 动作类型里需要“目标目录”的动作（做校验时用）
ACTIONS_WITH_DIR = [ACTION_MOVE, ACTION_COPY]
# 动作类型里需要“新文件名”的动作
ACTIONS_WITH_NEWNAME = [ACTION_RENAME]

# ---------- 模板变量说明 ----------
# 动作里的 {{file.name}} 会被替换成实际触发文件的信息
# 支持：{{file.name}} 文件名、{{file.ext}} 扩展名、{{file.path}} 完整路径、
#       {{file.size}} 大小(MB)、{{watch_dir}} 监控目录
TEMPLATE_VARS = ["{{file.name}}", "{{file.ext}}", "{{file.path}}", "{{file.size}}", "{{watch_dir}}"]


def new_id() -> str:
    """生成一条规则的唯一编号。

    用 uuid4() 生成 32 位随机字符串（如 9c1b6f2e...），几乎不可能重复。
    取前 8 位就足够唯一，而且短一点显示友好。
    """
    return uuid.uuid4().hex[:8]


def now_str() -> str:
    """返回当前时间字符串，格式：2026-08-25T10:30:00（精确到秒）。"""
    return datetime.now().isoformat(timespec="seconds")


def validate_rule(rule: dict) -> str | None:
    """检查一条规则是否合法。

    参数：
        rule: 用户提交的规则字典
    返回：
        合法返回 None；不合法返回错误说明文字（前端会显示给用户）
    """
    # 规则必须有名字，而且不能是空字符串
    if not rule.get("name", "").strip():
        return "规则名字不能为空"

    # 取出触发器配置；没有触发器的规则没有意义
    trigger = rule.get("trigger") or {}
    # 触发器类型必须在白名单里（防止用户填了不存在的类型）
    if trigger.get("type") not in TRIGGER_TYPES:
        return "触发器类型无效"

    # 如果是文件类触发器，必须有监控目录（没目录就不知道盯谁）
    if trigger.get("type") in (TRIGGER_FILE_ADDED, TRIGGER_FILE_MODIFIED):
        if not trigger.get("watch_dir", "").strip():
            return "文件触发器必须指定监控目录"

    # 逐条检查条件列表（没有条件也可以，表示“任何文件都触发”）
    for cond in rule.get("conditions") or []:
        # 条件必须指定字段和操作符
        field = cond.get("field")
        op = cond.get("op")
        # 字段必须在白名单里
        if field not in FIELD_ALLOWED_OPS:
            return f"条件字段无效: {field}"
        # 操作符必须是该字段允许的
        if op not in FIELD_ALLOWED_OPS[field]:
            return f"字段 {field} 不支持操作符 {op}"
        # 值不能为空
        if cond.get("value") in (None, "", []):
            return f"条件 {field} 的值不能为空"

    # 动作列表至少要有一个（没有动作的规则等于白触发）
    if not rule.get("actions"):
        return "至少需要一个动作"

    # 逐条检查动作
    for act in rule.get("actions") or []:
        # 动作类型必须是已知的
        if act.get("type") not in (ACTION_MOVE, ACTION_COPY, ACTION_RENAME, ACTION_NOTIFY):
            return f"动作类型无效: {act.get('type')}"
        # 移动/复制必须给目标目录
        if act.get("type") in ACTIONS_WITH_DIR and not act.get("dest_dir", "").strip():
            return "移动/复制动作必须指定目标目录"
        # 重命名必须给新文件名
        if act.get("type") == ACTION_RENAME and not act.get("new_name", "").strip():
            return "重命名动作必须指定新文件名"

    # 全部检查通过，返回 None 表示合法
    return None


def build_rule(name: str, trigger: dict, conditions: list, actions: list, enabled: bool = True) -> dict:
    """把用户填的内容组装成一条完整的规则字典（自动补上 id 和时间）。

    这是“创建规则”时统一走的入口，保证每条规则结构一致。
    """
    # 组装字典并返回；JSON 序列化在存储层（rules.py）处理
    return {
        "id": new_id(),                                  # 自动生成唯一编号
        "name": name.strip(),                            # 去掉名字首尾空格
        "enabled": enabled,                              # 是否启用
        "trigger": trigger,                              # 触发器配置
        "conditions": conditions or [],                  # 条件列表（没有就给空列表）
        "actions": actions,                              # 动作列表
        "created_at": now_str(),                         # 创建时间
        "updated_at": now_str(),                         # 更新时间（刚创建=创建时间）
    }
