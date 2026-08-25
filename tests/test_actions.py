# -*- coding: utf-8 -*-
"""测试：动作模板替换（app/engine/actions.py 的 render_template）。"""

# 导入被测函数：把 {{file.name}} 等模板变量替换成真实值
from app.engine.actions import render_template

# 构造一份"文件信息"（模拟触发规则的文件）
INFO = {"name": "报告.txt", "ext": ".txt", "path": "D:/下载/报告.txt", "size": 1.5}


def test_replace_file_name():
    """{{file.name}} 替换成文件名。"""
    result = render_template("已处理 {{file.name}}", INFO, "D:/下载")
    assert result == "已处理 报告.txt"


def test_replace_file_ext():
    """{{file.ext}} 替换成扩展名。"""
    result = render_template("备份{{file.ext}}", INFO, "D:/下载")
    assert result == "备份.txt"


def test_replace_watch_dir():
    """{{watch_dir}} 替换成监控目录。"""
    result = render_template("目标: {{watch_dir}}", INFO, "D:/下载")
    assert result == "目标: D:/下载"


def test_replace_multiple_vars():
    """一条消息里多个变量一起替换。"""
    result = render_template(
        "{{file.name}} ({{file.size}}MB) 在 {{watch_dir}}", INFO, "D:/下载"
    )
    assert result == "报告.txt (1.5MB) 在 D:/下载"


def test_unknown_placeholder_kept():
    """未定义的占位符保持原样（不报错、不误替换）。"""
    result = render_template("{{file.name}} {{unknown_var}}", INFO, "D:/下载")
    assert result == "报告.txt {{unknown_var}}"


def test_empty_text():
    """空文本也能正常处理。"""
    assert render_template("", INFO, "D:/下载") == ""
