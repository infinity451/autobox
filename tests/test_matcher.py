# -*- coding: utf-8 -*-
"""测试：条件匹配模块（app/engine/matcher.py）。

测试的都是"纯函数"（输入固定输出固定），最适合单元测试。
运行方式：在项目根目录执行  python -m pytest tests/
"""

# 导入 pytest：测试框架
import pytest

# 导入被测模块：
# extract_file_info（提取文件信息）、match_conditions（判断条件是否满足）
from app.engine.matcher import extract_file_info, match_conditions


def test_match_conditions_no_conditions_always_true():
    """没有条件 = 任何文件都满足。"""
    # 条件列表为空
    conditions = []
    # 随便一个文件信息
    info = {"name": "随便.txt", "ext": ".txt", "path": "D:/随便.txt", "size": 1.0}
    # 空条件应该永远返回 True
    assert match_conditions(conditions, info) is True


def test_match_conditions_ext_in():
    """扩展名"属于"某列表：匹配和不匹配两种。"""
    # 条件：扩展名是 .mp4 或 .mkv
    conditions = [{"field": "ext", "op": "in", "value": [".mp4", ".mkv"]}]
    # .mp4 文件 → 满足
    assert match_conditions(conditions, {"ext": ".mp4"}) is True
    # .mkv 文件 → 满足
    assert match_conditions(conditions, {"ext": ".mkv"}) is True
    # .txt 文件 → 不满足
    assert match_conditions(conditions, {"ext": ".txt"}) is False


def test_match_conditions_name_contains():
    """文件名"包含"关键词。"""
    conditions = [{"field": "name", "op": "contains", "value": "视频"}]
    # 名字含"视频" → 满足
    assert match_conditions(conditions, {"name": "第8课视频.mp4"}) is True
    # 名字不含 → 不满足
    assert match_conditions(conditions, {"name": "报告.txt"}) is False


def test_match_conditions_size_gt():
    """文件大小"大于"阈值（注意要转数字比较）。"""
    conditions = [{"field": "size", "op": "gt", "value": 100}]
    # 150MB > 100 → 满足
    assert match_conditions(conditions, {"size": 150.0}) is True
    # 50MB > 100 → 不满足
    assert match_conditions(conditions, {"size": 50.0}) is False


def test_match_conditions_all_required():
    """多个条件 = AND 逻辑：全部满足才 True，一个不满足就 False。"""
    conditions = [
        {"field": "ext", "op": "in", "value": [".mp4", ".mkv"]},
        {"field": "name", "op": "contains", "value": "视频"},
        {"field": "size", "op": "gt", "value": 10},
    ]
    # 全部满足
    info_ok = {"name": "第8课视频.mp4", "ext": ".mp4", "size": 200.0}
    assert match_conditions(conditions, info_ok) is True
    # 扩展名不满足（.txt）→ 整体 False
    info_bad_ext = {"name": "第8课视频.txt", "ext": ".txt", "size": 200.0}
    assert match_conditions(conditions, info_bad_ext) is False
    # 大小不满足 → 整体 False
    info_bad_size = {"name": "第8课视频.mp4", "ext": ".mp4", "size": 1.0}
    assert match_conditions(conditions, info_bad_size) is False


def test_extract_file_info(tmp_path):
    """extract_file_info 能正确提取文件信息（用 pytest 的临时目录造真实文件）。"""
    # 在临时目录里创建一个真实文件
    f = tmp_path / "我的笔记.txt"
    f.write_text("hello", encoding="utf-8")
    # 提取信息
    info = extract_file_info(str(f))
    # 文件名（含扩展名）
    assert info["name"] == "我的笔记.txt"
    # 扩展名（小写、带点）
    assert info["ext"] == ".txt"
    # 路径应该是完整路径
    assert info["path"].endswith("我的笔记.txt")
    # 大小：5 字节转成 MB 后是 0.0（不足 1MB），这是正常行为
    assert info["size"] == 0.0
