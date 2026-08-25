# -*- coding: utf-8 -*-
"""动作执行：执行规则里的“动作”（移动/复制/重命名/通知）。

动作是规则的最后一步：条件满足了，就按这里写的做。
比如规则说“移动到 D:/视频”，执行动作时就把触发规则的那个文件搬过去。

本文件提供：
- render_template()：把 {{file.name}} 这种模板变量替换成真实值
- run_actions()：按顺序执行一条规则的所有动作，并返回执行结果列表
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 shutil：Python 自带的“文件和文件夹操作”工具库（移动/复制都靠它）
import shutil
# 导入 Path：路径处理
from pathlib import Path

# 导入数据库模块（执行动作时要写日志）
from .. import database
# 导入动作类型常量（move/copy/rename/notify），写代码时不用记字符串
from ..models import ACTION_COPY, ACTION_MOVE, ACTION_NOTIFY, ACTION_RENAME


def render_template(text: str, info: dict, watch_dir: str) -> str:
    """把模板字符串里的 {{xxx}} 替换成真实值。

    参数：
        text:      模板字符串，如 "已归档 {{file.name}}"
        info:      文件信息字典（name/ext/path/size）
        watch_dir: 监控目录（规则触发器的 watch_dir）
    返回：
        替换后的字符串，如 "已归档 第8课.mp4"

    这就是“模板引擎”的最简版：把占位符换成真实数据。
    """
    # 定义“占位符 → 真实值”的映射表（字典：键是占位符，值是替换内容）
    mapping = {
        "{{file.name}}": info.get("name", ""),          # 文件名
        "{{file.ext}}": info.get("ext", ""),            # 扩展名
        "{{file.path}}": info.get("path", ""),          # 完整路径
        "{{file.size}}": str(info.get("size", "")),     # 大小（转成字符串才能替换）
        "{{watch_dir}}": watch_dir,                     # 监控目录
    }
    # 遍历映射表，把文本里出现的每个占位符都替换成真实值
    for key, value in mapping.items():
        # str.replace(旧, 新)：把 text 里所有 key 替换成 value
        text = text.replace(key, value)
    # 返回替换完的文本
    return text


def _execute_move(info: dict, act: dict, watch_dir: str) -> tuple[bool, str]:
    """执行“移动文件”动作。返回 (是否成功, 说明文字)。"""
    # 替换目标目录里的模板变量（比如目标目录可能写成 "D:/{{file.ext}} 类文件"）
    dest_dir = render_template(act["dest_dir"], info, watch_dir)
    # 目标目录不存在就创建（mkdir parents=True 连上级目录一起建，exist_ok=True 已存在不报错）
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    # 源文件路径（就是触发规则的那个文件）
    src = Path(info["path"])
    # 目标路径 = 目标目录 / 原文件名
    dest = Path(dest_dir) / src.name
    # 执行移动：shutil.move(源, 目标)
    shutil.move(str(src), str(dest))
    # 返回成功和说明（说明里显示从哪里移到哪里）
    return True, f"已移动 → {dest}"


def _execute_copy(info: dict, act: dict, watch_dir: str) -> tuple[bool, str]:
    """执行“复制文件”动作。返回 (是否成功, 说明文字)。"""
    # 和移动几乎一样，区别是 shutil.copy2 是复制（原文件保留）
    dest_dir = render_template(act["dest_dir"], info, watch_dir)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    src = Path(info["path"])
    dest = Path(dest_dir) / src.name
    # copy2 会连文件的修改时间等元信息一起复制
    shutil.copy2(str(src), str(dest))
    # 返回成功和说明
    return True, f"已复制 → {dest}"


def _execute_rename(info: dict, act: dict, watch_dir: str) -> tuple[bool, str]:
    """执行“重命名文件”动作。返回 (是否成功, 说明文字)。"""
    # 新文件名也支持模板变量（比如 "{{file.name}}" 换个规则改名字）
    new_name = render_template(act["new_name"], info, watch_dir)
    # 源文件
    src = Path(info["path"])
    # 目标路径 = 源文件所在目录 / 新名字
    dest = src.parent / new_name
    # 重命名本质也是移动（同一目录内移动 = 改名）
    shutil.move(str(src), str(dest))
    # 返回成功和说明
    return True, f"已重命名 → {new_name}"


def _execute_notify(info: dict, act: dict, watch_dir: str) -> tuple[bool, str]:
    """执行“通知”动作：当前版本写入日志（后续版本升级为系统弹窗）。"""
    # 通知内容支持模板变量（比如 "{{file.name}} 已处理"）
    message = render_template(act.get("message", "任务完成"), info, watch_dir)
    # 目前先记一条 info 日志，以后在这里加系统弹窗代码即可
    database.log(None, "通知", "info", message)
    # 返回成功和说明
    return True, f"通知: {message}"


def run_actions(rule: dict, info: dict, watch_dir: str) -> list[dict]:
    """按顺序执行一条规则的所有动作。

    参数：
        rule:      规则字典（里面是 conditions/actions 等）
        info:      触发规则的文件信息
        watch_dir: 监控目录
    返回：
        每个动作的执行结果列表，如：
        [{"type": "move", "ok": True, "message": "已移动 → D:/视频/第8课.mp4"}]
    """
    # 结果列表，最后返回给调用方
    results = []
    # 逐个执行动作
    for act in rule["actions"]:
        # 根据动作类型调用对应的执行函数；每个函数返回 (成功?, 说明)
        if act["type"] == ACTION_MOVE:
            ok, message = _execute_move(info, act, watch_dir)
        elif act["type"] == ACTION_COPY:
            ok, message = _execute_copy(info, act, watch_dir)
        elif act["type"] == ACTION_RENAME:
            ok, message = _execute_rename(info, act, watch_dir)
        elif act["type"] == ACTION_NOTIFY:
            ok, message = _execute_notify(info, act, watch_dir)
        else:
            # 未知动作类型（理论上校验层已挡掉，这里是兜底）
            ok, message = False, f"未知动作类型: {act['type']}"
        # 把这次动作的结果记录进结果列表
        results.append({"type": act["type"], "ok": ok, "message": message})
    # 返回所有动作的结果
    return results
