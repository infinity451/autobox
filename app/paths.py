# -*- coding: utf-8 -*-
"""统一路径工具：开发模式和打包（exe）模式下，文件路径怎么找。

为什么需要这个文件：
- 开发模式：程序从项目根目录跑，static/、data/ 就在项目根下面
- 打包模式（exe）：程序被 PyInstaller 打包，运行时两个位置很特殊：
  1. sys._MEIPASS：exe 运行时"解压临时目录"——打包进去的 static/ 在这里
  2. exe 旁边：用户能看到的位置——data/（用户数据）必须放这里，否则数据会丢

本文件提供三个函数，全项目统一调用，不要再自己拼路径：
- resource_dir()：静态资源目录（static/ 在哪）
- data_dir()：数据目录（data/ 在哪）
- project_root()：项目根（开发模式用）
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 sys：判断是否在打包环境（sys.frozen）
import sys
# 导入 Path：路径处理
from pathlib import Path


def is_frozen() -> bool:
    """当前是否运行在打包后的 exe 里。

    PyInstaller 打包后会在 sys 上设置 frozen 属性（值为 True）。
    这个标志决定了其他函数用哪套路径逻辑。
    """
    return getattr(sys, "frozen", False)


def project_root() -> Path:
    """项目根目录（开发模式用）。

    打包模式下没有"项目根"概念，用 exe 旁边代替。
    """
    # 打包了就用 exe 所在目录，否则用本文件所在目录的上一级（app/ 的父级）
    if is_frozen():
        return Path(sys.executable).parent
    # __file__ 是 paths.py 的路径，parent 是 app/，再 parent 是项目根
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """静态资源目录（static/ 在哪）。

    打包模式：静态文件被打包进 exe，运行时解压到 sys._MEIPASS
    开发模式：就是项目根目录
    """
    # 打包模式下静态资源在解压临时目录里
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", "."))
    # 开发模式：项目根目录
    return project_root()


def data_dir() -> Path:
    """数据目录（data/ 在哪）。

    注意：打包模式下 data/ 必须放在 exe 旁边（用户可见、可备份的位置），
    不能放在解压临时目录里（那个目录每次运行都会被清掉，数据会丢）。
    """
    # 打包模式：exe 旁边
    if is_frozen():
        return Path(sys.executable).parent / "data"
    # 开发模式：项目根/data
    return project_root() / "data"
