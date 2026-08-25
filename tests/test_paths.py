# -*- coding: utf-8 -*-
"""测试：引擎路径规范化（app/engine/scheduler.py 的 _norm_path）。

覆盖 Windows 经典的"正斜杠/反斜杠不一致"问题。
"""

# 导入被测的 Engine 类（用静态方法 _norm_path，不需要实例化引擎）
from app.engine.scheduler import Engine


def test_norm_path_unifies_slashes():
    """正斜杠和反斜杠统一成一样的结果（都是小写正斜杠）。"""
    # 正斜杠写法
    a = Engine._norm_path("D:/Download")
    # 反斜杠写法
    b = Engine._norm_path("D:\\Download")
    # 规范化后必须相等（否则规则匹配不上，这是之前踩过的坑）
    assert a == b
    # 结果是小写正斜杠
    assert a == "d:/download"


def test_norm_path_uppercase_lowercase():
    """大小写不同的路径规范化后相等（Windows 不区分大小写）。"""
    assert Engine._norm_path("D:/Video") == Engine._norm_path("d:/video")


def test_norm_path_empty():
    """空字符串返回空字符串（不报错）。"""
    assert Engine._norm_path("") == ""
