# -*- coding: utf-8 -*-
"""回放器：把录制的事件序列重放出来（用 pynput 控制鼠标键盘）。

原理：
- 用 pynput 的 Controller 类"假装"用户操作：移动鼠标、点击、按键
- 每两个事件之间按录制时的 delay 等待，还原操作节奏
- 支持速度控制（speed=2 表示两倍速，delay 除以 2）
- 支持紧急停止：回放中按 F8 立即停止（防失控）

安全设计（重要）：
- 回放是"真的操作电脑"，可能点错按钮、打错字
- 所以：回放前必须由用户确认；提供紧急停止键；速度可控
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 time：等待（模拟操作间隔）
import time

# 导入 pynput 的 Controller：模拟鼠标键盘操作
from pynput import keyboard, mouse

# 创建"虚拟鼠标"和"虚拟键盘"（回放时用它们假装用户操作）
_mouse = mouse.Controller()
_keyboard = keyboard.Controller()

# 紧急停止标志：回放时按 F8 置为 True，回放循环看到就退出
_stop_flag = False
# 回放状态（前端显示用）
_playing = False

# 紧急停止快捷键：F8（比 Ctrl+C 安全，不会影响正在回放的自动化）
EMERGENCY_KEY = "f8"


def _on_emergency_key(key) -> None:
    """监听紧急停止键：按 F8 就停止回放。"""
    global _stop_flag
    # key 转成字符串和紧急键名比较
    try:
        name = key.name if hasattr(key, "name") else key.char
    except AttributeError:
        name = None
    # 按下了紧急键：置停止标志
    if name == EMERGENCY_KEY:
        _stop_flag = True


# 紧急停止监听器（程序启动时启动一次）
_emergency_listener = keyboard.Listener(on_press=_on_emergency_key)
_emergency_listener.daemon = True


def start_emergency_listener() -> None:
    """启动紧急停止监听（程序启动时调用一次）。"""
    _emergency_listener.start()


def _play_event(event: dict, speed: float) -> None:
    """回放单条事件。

    参数：
        event: 事件字典（type/x/y/button/key/pressed…）
        speed: 速度倍率（1=原速，2=两倍速）
    """
    # 先按事件类型分派
    etype = event["type"]

    if etype == "move":
        # 移动鼠标到指定坐标
        _mouse.position = (event["x"], event["y"])

    elif etype == "click":
        # 点击鼠标：pressed=True 是按下，False 是松开
        button = getattr(mouse.Button, event["button"], mouse.Button.left)  # 字符串→Button 对象
        if event["pressed"]:
            _mouse.press(button)
        else:
            _mouse.release(button)

    elif etype == "scroll":
        # 滚动滚轮：dy 向下为正
        _mouse.scroll(event.get("dx", 0), event.get("dy", 0))

    elif etype == "key":
        # 键盘按键：把 key 字符串转回 pynput 的 Key/KeyCode 对象
        key = _parse_key(event["key"])
        if key is not None:
            if event["pressed"]:
                _keyboard.press(key)
            else:
                _keyboard.release(key)

    # 事件执行完后，等待录制时的间隔（除以速度 = 快进）
    # delay 是"距录制开始的时间"，第一条事件是总时长；后续事件的间隔 = 后一条 delay - 前一条 delay
    # 简化处理：每条事件后统一等它自己的 delay 比例（见 play_macro 里的实现）


def _parse_key(key_str: str):
    """把字符串转回 pynput 的键对象。

    "a" → KeyCode(char='a')；"esc" → Key.esc；"f13" → Key.f13
    转失败返回 None（忽略这条事件，不报错）。
    """
    # 字符串为空返回 None
    if not key_str:
        return None
    # 先试试是不是功能键（esc、enter、f13 这种有名字的）
    try:
        return getattr(keyboard.Key, key_str)
    except AttributeError:
        pass
    # 不是功能键，当作普通字符键（KeyCode）
    return keyboard.KeyCode.from_char(key_str)


def play_macro(events: list, speed: float = 1.0, on_progress=None) -> dict:
    """回放整个宏。

    参数：
        events: 事件列表
        speed: 速度倍率（>=0.5）
        on_progress: 进度回调（可选，前端显示进度用）
    返回：
        {"ok": true, "played": 回放事件数} 或 {"ok": false, "error": 错误信息}
    """
    # 事件列表为空直接失败
    if not events:
        return {"ok": False, "error": "宏没有事件"}

    # 重置停止标志
    global _stop_flag
    _stop_flag = False
    # 标记正在回放
    global _playing
    _playing = True

    # 速度下限保护：防止填 0 或负数导致卡死
    speed = max(speed, 0.5)

    try:
        # 逐条回放
        for i, event in enumerate(events):
            # 检查紧急停止标志（按了 F8 就退出）
            if _stop_flag:
                return {"ok": False, "error": "已按 F8 紧急停止"}

            # 先等待：这条事件的 delay 减去上一条的 delay = 真正的间隔时间
            # 第一条事件 delay 是总时长，用它的比例当作起始等待
            delay = event.get("delay", 0.05)
            if i > 0:
                # 后续事件的间隔 = 本条 delay - 上条 delay（保证节奏）
                delay = event["delay"] - events[i - 1].get("delay", 0)
            # 间隔不能为负（时钟误差），最小 0
            delay = max(delay, 0)
            # 除以速度 = 快进（2 倍速就是等一半时间）
            time.sleep(delay / speed)

            # 执行这条事件
            _play_event(event, speed)

            # 进度回调（每 10 条回调一次，减少开销）
            if on_progress and i % 10 == 0:
                on_progress(i + 1, len(events))

        # 回放完成
        return {"ok": True, "played": len(events)}
    except Exception as e:  # noqa: BLE001
        # 回放出错（比如事件数据有问题）
        return {"ok": False, "error": f"回放失败: {e}"}
    finally:
        # 无论成功失败，最后都要标记"不在回放"（释放状态）
        _playing = False


def stop_playing() -> None:
    """请求停止回放（把停止标志置 True，回放循环很快会退出）。"""
    global _stop_flag
    _stop_flag = True


def is_playing() -> bool:
    """当前是否在回放中。"""
    return _playing
