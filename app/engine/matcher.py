# -*- coding: utf-8 -*-
"""条件匹配：判断一个文件/事件满不满足规则的条件。

“条件”就是规则里的 conditions 列表，比如：
    [{"field": "ext", "op": "in", "value": [".mp4", ".mkv"]}]
意思是：文件的扩展名必须是 .mp4 或 .mkv 才满足条件。

本文件只有一个核心函数 match_conditions，规则引擎处理事件时调用它。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 models 里的操作符常量（contains/equals/in/gt/lt），写代码时不用记字符串
from ..models import (
    FIELD_EXT,
    FIELD_NAME,
    FIELD_PATH,
    FIELD_SIZE,
    OP_CONTAINS,
    OP_EQUALS,
    OP_GREATER,
    OP_IN,
    OP_LESS,
)


def extract_file_info(path: str) -> dict:
    """根据文件完整路径，提取出做条件匹配需要的文件信息。

    参数：
        path: 文件完整路径，如 "D:/下载/第8课.mp4"
    返回：
        一个字典：{"name": 文件名, "ext": 扩展名, "path": 完整路径, "size": 大小(MB)}
    """
    # 导入 pathlib 的 Path 类（处理路径的官方工具，跨平台安全）
    from pathlib import Path

    # Path(path) 把字符串转成 Path 对象，就能用 .name/.suffix 等方法
    p = Path(path)
    # p.stat() 拿文件状态，.st_size 是文件大小（单位字节 byte）
    # 转成 MB：字节 ÷ 1024 ÷ 1024，保留 2 位小数
    size_mb = round(p.stat().st_size / 1024 / 1024, 2)
    # 组装并返回文件信息字典
    return {
        "name": p.name,          # 文件名（含扩展名），如 "第8课.mp4"
        "ext": p.suffix.lower(), # 扩展名（小写），如 ".mp4"；suffix 拿的是 ".mp4" 这种带点的
        "path": str(p),          # 完整路径（转回字符串）
        "size": size_mb,         # 大小（MB）
    }


def _match_one(cond: dict, info: dict) -> bool:
    """判断“单个条件”是否满足。

    参数：
        cond: 一个条件字典，如 {"field": "ext", "op": "in", "value": [".mp4"]}
        info: 文件信息字典（extract_file_info 的返回结果）
    返回：
        True = 满足，False = 不满足
    """
    # 从条件里取出字段名、操作符、期望值
    field = cond["field"]      # 看文件的哪个属性（名字/扩展名/大小/路径）
    op = cond["op"]            # 用什么方式比较（包含/等于/属于/大于/小于）
    value = cond["value"]      # 期望的值
    # 取出文件实际的属性值（info[field] 就是文件名/扩展名/大小/路径）
    actual = info[field]

    # 用 if-elif 分支处理每种操作符（比较逻辑很直白，看注释即可懂）
    if op == OP_CONTAINS:
        # “包含”：文件属性里有没有包含期望的字符串（忽略大小写，把两边都转小写比较）
        return str(value).lower() in str(actual).lower()

    if op == OP_EQUALS:
        # “等于”：两边一模一样
        return str(actual) == str(value)

    if op == OP_IN:
        # “属于”：实际值在期望的列表里（比如扩展名在 [".mp4", ".mkv"] 里）
        return str(actual) in [str(v) for v in value]

    if op == OP_GREATER:
        # “大于”：实际值 > 期望值（用于文件大小，注意都转成数字比较）
        return float(actual) > float(value)

    if op == OP_LESS:
        # “小于”：实际值 < 期望值
        return float(actual) < float(value)

    # 操作符不在上面任何分支里（理论上校验层已经挡掉了），返回 False 表示不满足
    return False


def match_conditions(conditions: list, info: dict) -> bool:
    """判断文件是否满足规则的全部条件。

    规则是“所有条件都要满足才执行”（AND 逻辑）。

    参数：
        conditions: 条件列表，如 [{"field": "ext", "op": "in", "value": [".mp4"]}]
        info: 文件信息字典
    返回：
        True = 满足全部条件（或没有条件），False = 有任一条件不满足
    """
    # 没有条件 = 无条件限制 = 任何文件都满足
    if not conditions:
        return True
    # 逐个条件判断，只要有一个不满足（False），整个就不满足
    for cond in conditions:
        # 有任意一个条件不满足，直接返回 False（AND 逻辑：一个不满足全盘否定）
        if not _match_one(cond, info):
            return False
    # 所有条件都满足了，返回 True
    return True
