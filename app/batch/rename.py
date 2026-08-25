# -*- coding: utf-8 -*-
"""批量重命名引擎：预览 + 执行。

核心思路（跟"规则管家"一样的安全原则）：
1. 先预览：根据配置算出每个文件「旧名 → 新名」的对照表，用户确认
2. 再执行：只有用户点了确认才真正改名

支持四种重命名模式：
- prefix    加前缀：  旧名 "报告.txt"   →  新名 "工作_报告.txt"
- suffix    加后缀：  旧名 "报告.txt"   →  新名 "报告_终版.txt"（加在扩展名前）
- replace   替换文本：把文件名里的某段文字换成另一段
- sequence  加序号：  旧名 "报告.txt"   →  新名 "01_报告.txt"（按顺序编号）
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 Path：路径处理
from pathlib import Path

# 四种模式的名字（前端下拉框的 value 用）
MODE_PREFIX = "prefix"        # 加前缀
MODE_SUFFIX = "suffix"        # 加后缀
MODE_REPLACE = "replace"      # 替换文本
MODE_SEQUENCE = "sequence"    # 加序号


def _new_name(old: str, mode: str, params: dict, index: int) -> str:
    """根据模式算出新文件名（不真正改名，只是"算"）。

    参数：
        old:    原文件名（含扩展名），如 "报告.txt"
        mode:   模式
        params: 模式参数，如 {"prefix": "工作_"}
        index:  序号（从 1 开始），加序号模式用
    返回：
        新文件名；如果算出来跟原来一样，也原样返回（执行时会跳过）
    """
    # 拆出"主名"和"扩展名"：
    # Path(old).stem  = "报告"（去掉扩展名的部分）
    # Path(old).suffix = ".txt"（扩展名，带点）
    stem = Path(old).stem
    ext = Path(old).suffix

    # 按模式分别计算
    if mode == MODE_PREFIX:
        # 加前缀：前缀 + 原文件名
        return params.get("prefix", "") + old

    if mode == MODE_SUFFIX:
        # 加后缀：主名 + 后缀 + 扩展名（后缀加在扩展名前面）
        return stem + params.get("suffix", "") + ext

    if mode == MODE_REPLACE:
        # 替换：把文件名里所有"旧文字"换成"新文字"
        # 注意只替换文件名部分（不含扩展名），扩展名一般不该动
        find = params.get("find", "")
        replace = params.get("replace", "")
        # 扩展名也参与替换吗？简单起见：只替换主名部分，扩展名保持原样
        return stem.replace(find, replace) + ext

    if mode == MODE_SEQUENCE:
        # 加序号：把序号补成 3 位数字（001、002…），放在最前面
        # 也可以配置序号放后面（params["position"] == "suffix"）
        seq = f"{index:03d}"
        if params.get("position") == "suffix":
            # 序号放后面：报告_001.txt
            return f"{stem}_{seq}{ext}"
        # 序号放前面（默认）：001_报告.txt
        return f"{seq}_{old}"

    # 未知模式：原样返回（安全起见不改名）
    return old


def preview_rename(directory: str, mode: str, params: dict, max_items: int = 200) -> dict:
    """预览：算出「旧名 → 新名」对照表，检查冲突。

    参数：
        directory: 要处理的文件夹
        mode:      模式
        params:    模式参数
        max_items: 最多处理多少个文件（防止一次太多）
    返回：
        {
          "ok": true,
          "files": [{"old": 旧名, "new": 新名, "conflict": 是否冲突}],
          "total": 文件总数,
          "conflicts": 冲突数
        }
    """
    # 目录必须存在，不存在直接返回失败
    if not Path(directory).is_dir():
        return {"ok": False, "error": f"目录不存在: {directory}"}

    # 只取文件夹下的一层文件（不递归子文件夹，安全）
    files = [p for p in Path(directory).iterdir() if p.is_file()]
    # 按文件名排序（保证序号模式顺序稳定）
    files.sort(key=lambda p: p.name)
    # 只处理前 max_items 个
    files = files[:max_items]

    # 记录用过的"新名字"，用于检测冲突（两个文件改成同一个名字）
    used_new = set()
    # 结果列表
    result_files = []
    # 冲突计数
    conflicts = 0

    # 逐个文件计算
    for i, p in enumerate(files, start=1):
        # 算新名字
        new = _new_name(p.name, mode, params, i)
        # 冲突判断：新名字在别处已经用过了（used_new 里有），说明会撞名
        # 或者新名字已存在于目标目录（文件夹里本来就有这个名）
        conflict = new in used_new or (new != p.name and Path(directory, new).exists())
        # 记入结果
        result_files.append({"old": p.name, "new": new, "conflict": conflict})
        # 把新名字加入"用过的"集合（就算冲突也要加，避免重复报）
        used_new.add(new)
        # 冲突计数
        if conflict:
            conflicts += 1

    # 返回预览结果
    return {
        "ok": True,
        "files": result_files,
        "total": len(result_files),
        "conflicts": conflicts,
    }


def execute_rename(directory: str, mode: str, params: dict, max_items: int = 200) -> dict:
    """执行重命名：真正改名。

    安全措施：
    - 跳过冲突项（不覆盖已有文件）
    - 跳过"新名等于旧名"的项（没变化不用改）
    - 逐个 try/except，单个失败不影响其他

    返回：
        {"ok": true, "renamed": 成功数, "skipped": 跳过数, "failed": [失败项列表]}
    """
    # 先预览（拿同一份对照表）
    preview = preview_rename(directory, mode, params, max_items)
    # 预览失败（目录不存在等）直接返回
    if not preview["ok"]:
        return preview

    # 计数
    renamed = 0      # 成功改名数
    skipped = 0      # 跳过数（没变化/冲突）
    failed = []      # 失败列表 [{name, error}]

    # 逐个执行
    for item in preview["files"]:
        # 跳过：新名等于旧名（没变化）
        if item["new"] == item["old"]:
            skipped += 1
            continue
        # 跳过：冲突（目标已存在，改名会覆盖别人的文件，危险）
        if item["conflict"]:
            skipped += 1
            continue
        # 源文件完整路径
        src = Path(directory) / item["old"]
        # 目标完整路径
        dst = Path(directory) / item["new"]
        # 执行改名；失败要单独记录，不能影响其他文件
        try:
            # rename 就是改名（同一目录内移动）
            src.rename(dst)
            # 成功计数
            renamed += 1
        except Exception as e:  # noqa: BLE001
            # 记录失败项
            failed.append({"name": item["old"], "error": str(e)})

    # 返回执行结果
    return {
        "ok": True,
        "renamed": renamed,
        "skipped": skipped,
        "failed": failed,
    }
