# -*- coding: utf-8 -*-
"""规则管理：对数据库里的规则做增删改查（CRUD）。

CRUD = Create(增) / Read(查) / Update(改) / Delete(删)。
本文件是唯一负责“把规则存进数据库/从数据库读出来”的地方，
其他代码要用规则时，都通过这里的函数，不直接碰数据库。
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 json：把 Python 字典和 JSON 文本互相转换。
# 规则里的 trigger/conditions/actions 在数据库里是 JSON 文本，
# 所以存的时候要“字典→JSON”，读的时候要“JSON→字典”
import json

# 导入上一级 app 包的 database 模块（点号表示相对导入：从 app 包导入 database）
from .. import database
# 导入 models 模块里的函数和常量（new_id、now_str 等）
from ..models import build_rule, validate_rule


def _row_to_rule(row) -> dict:
    """把数据库里的一行数据，转换成一个规则字典（方便代码使用）。

    参数：
        row: 数据库查询返回的一行（可以用 row["列名"] 取值）
    返回：
        一个字典，就是“规则长什么样”那节描述的格式
    """
    # 组装规则字典；json.loads 把 JSON 文本还原成 Python 列表/字典
    # enabled 在数据库里是 0/1（整数），这里转成 True/False（布尔值），前端显示更友好
    return {
        "id": row["id"],                                            # 编号
        "name": row["name"],                                        # 名字
        "enabled": bool(row["enabled"]),                            # 是否启用
        "trigger": json.loads(row["trigger"]),                      # 触发器（JSON→字典）
        "conditions": json.loads(row["conditions"]),                # 条件列表
        "actions": json.loads(row["actions"]),                      # 动作列表
        "created_at": row["created_at"],                            # 创建时间
        "updated_at": row["updated_at"],                            # 更新时间
    }


def list_rules() -> list[dict]:
    """查询所有规则（按创建时间倒序，新的排前面）。"""
    # 查询数据库：SELECT * 表示取所有列，ORDER BY created_at DESC 按创建时间倒序
    rows = database.query("SELECT * FROM rules ORDER BY created_at DESC")
    # 把每一行都转成规则字典，然后组成列表返回
    return [_row_to_rule(r) for r in rows]


def get_rule(rule_id: str) -> dict | None:
    """按 id 查询单条规则；找不到返回 None。"""
    # WHERE id = ? 表示只取 id 匹配的那一行；? 是占位符，参数在第二参数里传
    rows = database.query("SELECT * FROM rules WHERE id = ?", (rule_id,))
    # 有结果就转换并返回，没有就返回 None（表示找不到）
    return _row_to_rule(rows[0]) if rows else None


def create_rule(name: str, trigger: dict, conditions: list, actions: list, enabled: bool = True) -> dict:
    """创建一条新规则。

    返回：创建好的规则字典；如果校验不通过，抛出 ValueError（异常），
    调用方（API 层）会捕获并返回给前端显示错误。
    """
    # 用 models 里的 build_rule 组装成完整规则（自动生成 id 和时间）
    rule = build_rule(name, trigger, conditions, actions, enabled)
    # 校验规则是否合法；validate_rule 返回 None 表示合法，返回字符串表示错误原因
    error = validate_rule(rule)
    # 如果不合法，抛异常告诉上层“这条规则不行”，异常信息就是给用户看的错误
    if error:
        raise ValueError(error)

    # 插入数据库：把字典里的 trigger/conditions/actions 用 json.dumps 转成 JSON 文本存储
    # enabled 从 True/False 转成 1/0（SQLite 里用整数存布尔值）
    database.execute(
        "INSERT INTO rules (id, name, enabled, trigger, conditions, actions, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            rule["id"],
            rule["name"],
            1 if rule["enabled"] else 0,            # True→1，False→0
            json.dumps(rule["trigger"], ensure_ascii=False),    # ensure_ascii=False 保证中文不被转义
            json.dumps(rule["conditions"], ensure_ascii=False),
            json.dumps(rule["actions"], ensure_ascii=False),
            rule["created_at"],
            rule["updated_at"],
        ),
    )
    # 返回创建好的规则（前端可以用它刷新列表）
    return rule


def update_rule(rule_id: str, name: str, trigger: dict, conditions: list, actions: list, enabled: bool) -> dict:
    """更新一条已有规则（修改名字、触发器、条件、动作、启用状态）。

    返回：更新后的规则字典；规则不存在时返回 None。
    """
    # 先查一下这条规则在不在（不在就返回 None，避免改了不存在的行）
    old = get_rule(rule_id)
    if old is None:
        return None

    # 组装新规则内容：id 和时间沿用旧的（created_at 不变），其他用新值
    rule = {
        "id": rule_id,
        "name": name.strip(),
        "enabled": enabled,
        "trigger": trigger,
        "conditions": conditions or [],
        "actions": actions,
        "created_at": old["created_at"],            # 保留原创建时间
        "updated_at": database_updated_at(),        # 更新时间刷新为现在
    }
    # 同样先校验合法性
    error = validate_rule(rule)
    if error:
        raise ValueError(error)

    # 执行 UPDATE 更新数据库
    database.execute(
        "UPDATE rules SET name=?, enabled=?, trigger=?, conditions=?, actions=?, updated_at=? WHERE id=?",
        (
            rule["name"],
            1 if enabled else 0,
            json.dumps(trigger, ensure_ascii=False),
            json.dumps(conditions or [], ensure_ascii=False),
            json.dumps(actions, ensure_ascii=False),
            rule["updated_at"],
            rule_id,
        ),
    )
    # 返回更新后的规则
    return rule


def database_updated_at() -> str:
    """返回“现在的时间字符串”，供更新时间用。

    （单独抽出来是为了让导入关系简单，避免循环导入 models）
    """
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


def delete_rule(rule_id: str) -> bool:
    """删除一条规则。返回是否真的删掉了（False 表示规则不存在）。"""
    # 执行删除；execute 返回 lastrowid，但 DELETE 没有新行，所以这里看影响行数判断
    # 用 cursor.rowcount 判断更准确，这里简化：先查是否存在
    if get_rule(rule_id) is None:
        return False
    # 执行删除语句
    database.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    # 返回 True 表示删除成功
    return True


def toggle_rule(rule_id: str) -> dict | None:
    """切换规则的启用/暂停状态（启用→暂停，暂停→启用）。

    返回：切换后的规则；规则不存在返回 None。
    """
    # 查出当前规则
    rule = get_rule(rule_id)
    if rule is None:
        return None
    # 取反：启用变暂停，暂停变启用
    new_enabled = not rule["enabled"]
    # 调用 update_rule 更新（名字、触发器、条件、动作保持原样）
    return update_rule(
        rule_id,
        rule["name"],
        rule["trigger"],
        rule["conditions"],
        rule["actions"],
        new_enabled,
    )
