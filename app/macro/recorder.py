# -*- coding: utf-8 -*-
"""录制器：用 pynput 监听鼠标键盘，把操作录成事件序列。

原理（理解即可）：
- pynput 的 Listener 会在后台开监听线程，用户一动鼠标/键盘就调用我们注册的回调
- 我们在回调里记录事件（类型、坐标、按键）和"距上一个事件的时间差"（delay）
- 停止录制后，把事件序列交给前端保存

事件格式（一条条记录）：
  {"type": "move",  "x": 100, "y": 200, "delay": 0.05}       鼠标移动
  {"type": "click", "button": "left", "pressed": true, "x": 100, "y": 200, "delay": 0.1}  点击
  {"type": "scroll", "dx": 0, "dy": -1, "delay": 0.05}        滚轮
  {"type": "key",   "key": "a", "pressed": true, "delay": 0.05}  键盘按键
"""

# from __future__ import annotations：允许提前使用新式类型注解
from __future__ import annotations

# 导入 time：记录事件时间，算 delay（事件间隔）
import time

# 导入 pynput 的监听器：
# mouse.Listener 监听鼠标，keyboard.Listener 监听键盘
from pynput import keyboard, mouse

# 全局录制状态（整个程序同时只录一个宏）
# "state" 用一个字典存：是否在录制、开始时间、事件列表
_state = {"recording": False, "start_time": 0.0, "events": []}


def _record(event: dict) -> None:
    """内部函数：把一条事件加入事件列表（自动算好 delay）。"""
    # 如果不在录制状态，忽略（防止监听线程在其他时刻也记录）
    if not _state["recording"]:
        return
    # 当前时间
    now = time.time()
    # delay = 距开始录制的时间差（第一条事件的 delay = 总时长）
    # 这样回放时就能还原"操作节奏"
    delay = round(now - _state["start_time"], 3)
    # 把 delay 塞进事件，加入列表
    event["delay"] = delay
    _state["events"].append(event)


# ---------- 鼠标回调 ----------

def _on_move(x: int, y: int) -> None:
    """鼠标移动时被 pynput 调用。"""
    _record({"type": "move", "x": x, "y": y})


def _on_click(x: int, y: int, button, pressed: bool) -> None:
    """鼠标点击时被调用。"""
    # button 是 pynput 的 Button 对象，转成字符串（"left"/"right"/"middle"）
    _record({"type": "click", "button": str(button).replace("Button.", ""),
             "pressed": pressed, "x": x, "y": y})


def _on_scroll(x: int, y: int, dx: int, dy: int) -> None:
    """滚轮滚动时被调用。"""
    _record({"type": "scroll", "dx": dx, "dy": dy})


# ---------- 键盘回调 ----------

def _on_key_press(key) -> None:
    """键盘按下时被调用。"""
    # 转成字符串：普通字符键（"a"）或功能键名（如 "esc"、"f13"）
    _record({"type": "key", "key": _key_to_str(key), "pressed": True})


def _on_key_release(key) -> None:
    """键盘松开时被调用。"""
    _record({"type": "key", "key": _key_to_str(key), "pressed": False})


def _key_to_str(key) -> str:
    """把 pynput 的 key 对象转成字符串。

    普通字符键是 KeyCode 对象（如字母 a），功能键是 Key 对象（如 esc）。
    """
    try:
        # KeyCode 对象：key.char 是字符本身
        return key.char
    except AttributeError:
        # Key 对象：key.name 是功能键名字（如 "esc"、"f13"）
        return key.name


# ---------- 对外接口 ----------

def start_recording() -> None:
    """开始录制。"""
    # 已在录制中就不重复开始
    if _state["recording"]:
        return
    # 重置状态：记录开始时间，清空事件列表
    _state["recording"] = True
    _state["start_time"] = time.time()
    _state["events"] = []


def stop_recording() -> list:
    """停止录制。返回录到的事件列表。"""
    # 标记停止
    _state["recording"] = False
    # 返回事件列表（没有事件就是空列表）
    return _state["events"]


def is_recording() -> bool:
    """当前是否在录制中。"""
    return _state["recording"]


# ---------- 监听器（程序启动时启动一次，一直监听） ----------

# 创建鼠标和键盘监听器，把回调函数传进去
_mouse_listener = mouse.Listener(on_move=_on_move, on_click=_on_click, on_scroll=_on_scroll)
_keyboard_listener = keyboard.Listener(on_press=_on_key_press, on_release=_on_key_release)


def start_listeners() -> None:
    """启动监听线程（程序启动时调用一次）。"""
    # 非守护线程会阻塞退出，所以设置 daemon 让程序能正常退出
    _mouse_listener.daemon = True
    _keyboard_listener.daemon = True
    # 启动两个监听线程（start 后就在后台一直监听）
    _mouse_listener.start()
    _keyboard_listener.start()
