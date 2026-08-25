# -*- coding: utf-8 -*-
"""测试：批量重命名引擎（app/batch/rename.py）。

覆盖：四种命名模式的算法、预览的冲突检测、执行的安全行为。
"""

# 导入被测模块
from app.batch.rename import _new_name, execute_rename, preview_rename


# ---------- 四种命名模式的算法 ----------

def test_prefix():
    """加前缀：报告.txt → 工作_报告.txt"""
    assert _new_name("报告.txt", "prefix", {"prefix": "工作_"}, 1) == "工作_报告.txt"


def test_suffix():
    """加后缀（加在扩展名前）：报告.txt → 报告_终版.txt"""
    assert _new_name("报告.txt", "suffix", {"suffix": "_终版"}, 1) == "报告_终版.txt"


def test_replace():
    """替换文本：报告副本.txt → 报告.txt"""
    assert _new_name("报告副本.txt", "replace", {"find": "副本", "replace": ""}, 1) == "报告.txt"


def test_sequence_prefix():
    """加序号（放前面）：报告.txt → 001_报告.txt"""
    assert _new_name("报告.txt", "sequence", {"position": "prefix"}, 3) == "003_报告.txt"


def test_sequence_suffix():
    """加序号（放后面）：报告.txt → 报告_003.txt"""
    assert _new_name("报告.txt", "sequence", {"position": "suffix"}, 3) == "报告_003.txt"


# ---------- 预览与冲突检测 ----------

def test_preview_ok(tmp_path):
    """预览：能列出旧名→新名对照表。"""
    # 造两个文件
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    # 预览：加前缀
    result = preview_rename(str(tmp_path), "prefix", {"prefix": "P_"})
    assert result["ok"] is True
    assert result["total"] == 2
    # 两个文件都算出新名字，无冲突
    names = {f["old"]: f["new"] for f in result["files"]}
    assert names["a.txt"] == "P_a.txt"
    assert names["b.txt"] == "P_b.txt"
    assert result["conflicts"] == 0


def test_preview_conflict_detected(tmp_path):
    """预览：改名撞上"已有同名文件" → 检测出冲突。"""
    # 造两个文件：a.txt 和 x.txt（x.txt 已经存在，占着"新名"）
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "x.txt").write_text("已有")
    # 把 a 替换成 x（撞上已有的 x.txt）
    result = preview_rename(str(tmp_path), "replace", {"find": "a", "replace": "x"})
    # 至少有一个冲突（a.txt 要变成 x.txt，但 x.txt 已存在）
    assert result["conflicts"] >= 1
    # 冲突项被标记
    conflict_items = [f for f in result["files"] if f["conflict"]]
    assert len(conflict_items) >= 1


def test_preview_dir_not_exist():
    """目录不存在：预览直接返回失败（不抛异常）。"""
    result = preview_rename("D:/不存在的目录xyz", "prefix", {"prefix": "P_"})
    assert result["ok"] is False


# ---------- 执行 ----------

def test_execute_rename(tmp_path):
    """执行：真实改名成功。"""
    # 造两个文件
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    # 执行加前缀
    result = execute_rename(str(tmp_path), "prefix", {"prefix": "P_"})
    assert result["ok"] is True
    assert result["renamed"] == 2
    # 验证文件真的改名了
    assert (tmp_path / "P_a.txt").exists()
    assert (tmp_path / "P_b.txt").exists()
    assert not (tmp_path / "a.txt").exists()


def test_execute_skip_conflict(tmp_path):
    """执行：冲突项跳过不覆盖（安全第一）。"""
    # 造两个文件：a.txt 和 x.txt（x.txt 已有内容）
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "x.txt").write_text("已有")
    # 把 a 替换成 x（撞上已有的 x.txt）
    result = execute_rename(str(tmp_path), "replace", {"find": "a", "replace": "x"})
    # 冲突项被跳过：a.txt 不能改名（改名数 0）
    assert result["renamed"] == 0
    # 已有的 x.txt 内容没被破坏（安全保证）
    assert (tmp_path / "x.txt").read_text() == "已有"
    # a.txt 还在原位置
    assert (tmp_path / "a.txt").exists()
