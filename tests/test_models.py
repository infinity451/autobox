# -*- coding: utf-8 -*-
"""测试：规则校验（app/models.py 的 validate_rule）。

重点覆盖优化清单 #4（目录校验）和 #5（定时规则禁止文件动作）新增的校验逻辑。
"""

# 导入被测函数
from app.models import validate_rule

# ---------- 合法的规则 ----------

def make_valid_rule():
    """构造一条完全合法的规则（文件触发 + 移动动作）。"""
    return {
        "name": "视频归档",
        "trigger": {"type": "file_added", "watch_dir": "D:/下载"},
        "conditions": [{"field": "ext", "op": "in", "value": [".mp4"]}],
        "actions": [{"type": "move", "dest_dir": "D:/视频"}],
    }


def test_valid_rule_passes():
    """合法规则：校验通过（返回 None）。"""
    assert validate_rule(make_valid_rule()) is None


def test_empty_name_rejected():
    """规则名字为空：拒绝。"""
    rule = make_valid_rule()
    rule["name"] = "   "
    assert validate_rule(rule) is not None


def test_missing_watch_dir_rejected():
    """文件触发器没有监控目录：拒绝。"""
    rule = make_valid_rule()
    rule["trigger"]["watch_dir"] = ""
    assert validate_rule(rule) is not None


def test_no_actions_rejected():
    """没有动作：拒绝。"""
    rule = make_valid_rule()
    rule["actions"] = []
    assert validate_rule(rule) is not None


# ---------- 优化清单 #5：定时规则禁止文件动作 ----------

def test_schedule_with_move_rejected():
    """定时触发 + 移动动作：拒绝（没有具体文件可移）。"""
    rule = make_valid_rule()
    # 改成定时触发
    rule["trigger"] = {"type": "schedule", "cron": "0 9 * * *"}
    # 动作还是移动文件
    assert validate_rule(rule) is not None


def test_schedule_with_rename_rejected():
    """定时触发 + 重命名动作：拒绝。"""
    rule = make_valid_rule()
    rule["trigger"] = {"type": "schedule", "cron": "0 9 * * *"}
    rule["actions"] = [{"type": "rename", "new_name": "新名.txt"}]
    assert validate_rule(rule) is not None


def test_schedule_with_notify_passes():
    """定时触发 + 通知动作：合法（定时提醒是合理用法）。"""
    rule = make_valid_rule()
    rule["trigger"] = {"type": "schedule", "cron": "0 9 * * *"}
    rule["actions"] = [{"type": "notify", "message": "该喝水了"}]
    assert validate_rule(rule) is None


# ---------- 优化清单 #4：目标目录校验 ----------

def test_dest_dir_equals_watch_dir_rejected():
    """移动目标目录 = 监控目录本身：拒绝（移了等于没移）。"""
    rule = make_valid_rule()
    rule["actions"] = [{"type": "move", "dest_dir": "D:/下载"}]
    assert validate_rule(rule) is not None


def test_dest_dir_same_with_backslash_rejected():
    """目标目录用反斜杠写、监控目录用正斜杠写，仍是同一个目录：拒绝。"""
    rule = make_valid_rule()
    # 监控目录是正斜杠 D:/下载，目标用反斜杠 D:\下载
    rule["actions"] = [{"type": "move", "dest_dir": "D:\\下载"}]
    assert validate_rule(rule) is not None


def test_dest_dir_different_passes():
    """目标目录和监控目录不同：合法。"""
    rule = make_valid_rule()
    rule["actions"] = [{"type": "move", "dest_dir": "D:/视频"}]
    assert validate_rule(rule) is None


def test_dest_dir_missing_rejected():
    """移动动作没填目标目录：拒绝。"""
    rule = make_valid_rule()
    rule["actions"] = [{"type": "move", "dest_dir": ""}]
    assert validate_rule(rule) is not None
