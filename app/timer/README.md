# app/timer/ 定时提醒中心包说明

定时提醒中心（第 3 阶段）：到点自动做事情——提醒 / 关机 / 重启 / 休眠 / 打开程序。

## 文件清单

| 文件 | 作用 |
|---|---|
| `__init__.py` | 包的身份证 |
| `tasks.py` | 定时任务管理：增删改查 + 校验（存数据库 timer_tasks 表） |
| `runner.py` | 执行器：`show_notify` 弹窗、`execute_action` 执行动作、`schedule_task` 定时调度 |

## 五种动作类型

| 动作 | 做什么 | 关键实现 |
|---|---|---|
| `notify` 提醒 | 弹 Windows 系统消息框 | `ctypes.windll.user32.MessageBoxW`（无第三方依赖） |
| `shutdown` 关机 | 60 秒后关机 | `shutdown /s /t 60`（留反悔时间，可用 `shutdown /a` 取消） |
| `restart` 重启 | 60 秒后重启 | `shutdown /r /t 60` |
| `sleep` 休眠 | 立即休眠 | `shutdown /h` |
| `open` 打开程序 | 启动指定程序 | `subprocess.Popen` |

## 关键设计

- **弹窗不装依赖**：用 ctypes 直接调 Windows API，所有 Windows 电脑可用（0x40 图标代码 = 蓝色信息图标）
- **关机留缓冲**：关机/重启都有 60 秒延时，用户来得及取消——"宁可少做，不可误伤"
- **调度复用**：复用规则引擎的 APScheduler（job id 前缀 `timer_`，与其他模块区分），不重复造轮子
- **同步机制**：`sync_schedules()` 在启动和任务增删改后调用，全部取消再重注册（简单可靠）

## 提醒

- 关机/重启/休眠是**影响整个电脑**的操作，测试时请谨慎（建议先用提醒和打开程序测试）
- 取消已发出的关机命令：运行 `shutdown /a`
