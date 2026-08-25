# AutoBox 自动化工具箱

> 一个本地运行的「如果…就…」自动化平台：规则管家自动处理文件、网页采集器抓取数据、
> 批量文件魔法处理杂事、宏录制器回放操作、定时提醒中心定时关机。
> **数据全部存在本机，不上传云端。**

## 现在能用什么（第 1 阶段）

**📁 规则管家** 已可用：创建「如果…就…」规则，自动处理文件。
- 触发器：有新文件出现 / 文件被修改 / 定时触发（cron）
- 条件：文件名包含 / 扩展名属于 / 大小大于小于（可多条件，全部满足才执行）
- 动作：移动 / 复制 / 重命名 / 通知（按顺序执行，支持 `{{file.name}}` 模板变量）

示例规则：「下载文件夹有新文件，且扩展名是 .mp4/.mkv → 自动移动到 D:/视频」

其余模块（网页采集器 / 批量文件魔法 / 宏录制器 / 定时提醒中心）已规划，后续阶段开发。

## 快速开始

```bash
# 1. 安装依赖（在项目根目录）
pip install -r requirements.txt

# 2. 启动（保持窗口开着）
python main.py

# 3. 浏览器打开
http://127.0.0.1:8000
```

想立刻体验：网页 → 规则管家 → 新建规则，监控目录填 `D:/Learn/autobox/data/test_download`，
动作「移动」目标填 `D:/Learn/autobox/data/test_moved`，然后往 test_download 丢一个 .txt 文件，
几秒后看日志和 test_moved 目录——文件被自动移动了。

## 项目结构（每个文件夹都有 README 说明）

```
autobox/
├─ README.md                ← 本文件：项目总览
├─ requirements.txt         ← 依赖清单（pip install 安装）
├─ main.py                  ← 程序入口（python main.py 启动）
├─ fetch_github.py          ← 工具脚本：搜 GitHub 同类项目（研究用）
├─ fetch_repos.py           ← 工具脚本：查知名开源项目详情（研究用）
├─ app/                     ← 后端（Python）
│  ├─ README.md             ← app 目录说明
│  ├─ __init__.py           ← 包身份证
│  ├─ database.py           ← 数据层：SQLite 建表/读写/日志
│  ├─ models.py             ← 规则模型：触发器/条件/动作定义与校验
│  ├─ api.py                ← 接口层：网页请求 ↔ Python 调用
│  └─ engine/               ← 自动化引擎（心脏）
│     ├─ README.md          ← engine 目录说明
│     ├─ __init__.py        ← 包身份证
│     ├─ rules.py           ← 规则管理：增删改查
│     ├─ matcher.py         ← 条件匹配：文件满不满足条件
│     ├─ actions.py         ← 动作执行：移动/复制/重命名/通知
│     ├─ triggers.py        ← 触发器：文件监控(watchdog) + 定时(APScheduler)
│     └─ scheduler.py       ← 引擎主控：串起全链路 + 防死循环
├─ static/                  ← 前端（网页）
│  ├─ README.md             ← static 目录说明
│  ├─ index.html            ← 首页·功能中心
│  ├─ rules.html            ← 规则管家页面
│  ├─ css/
│  │  ├─ README.md          ← css 目录说明
│  │  └─ style.css          ← 全局样式
│  └─ js/
│     ├─ README.md          ← js 目录说明
│     ├─ api.js             ← 请求后端接口的工具函数
│     ├─ index.js           ← 首页脚本
│     └─ rules.js           ← 规则管家脚本
└─ data/                    ← 数据（自动生成）
   ├─ README.md             ← data 目录说明
   ├─ autobox.db            ← 主数据库（规则/日志）
   ├─ test_download/        ← 测试用模拟下载目录
   └─ test_moved/           ← 测试用模拟目标目录
```

## 代码阅读顺序（新手友好）

后端：`main.py` → `app/models.py` → `app/engine/rules.py` → `app/engine/matcher.py`
→ `app/engine/actions.py` → `app/engine/triggers.py` → `app/engine/scheduler.py`
前端：`static/js/api.js` → `static/js/index.js` → `static/js/rules.js`

**所有代码都有逐行中文注释**，按这个顺序读就能理解整个项目。

## 路线图

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 | 骨架 + 共享底座 + 规则管家（文件自动化） | ✅ 完成（可跑通） |
| 2 | 网页采集器（配置式爬虫 → Excel，参考 EasySpider 交互） | ⏳ |
| 3 | 批量文件魔法 + 定时提醒中心（含定时关机） | ⏳ |
| 4 | 宏录制器（参考 maCrow，pynput） | ⏳ |
| 5 | 界面打磨 + 打包 exe + 模板分享 | ⏳ |
| 后续 | 网页变化触发器（参考 Huginn 事件模型）、规则联动（参考 n8n 节点理念）、通知模块接 Apprise 库 | 规划中 |

## 灵感来源（GitHub 同类项目，研究记录）

| 项目 | 借鉴点 |
|---|---|
| n8n（⭐202k） | 工作流自动化平台：规则联动、节点化设计理念 |
| Huginn（⭐50k） | 网页变化监控 Agent：事件携带数据模型 |
| EasySpider（⭐44k） | 可视化无代码爬虫：点选元素生成选择器交互 |
| Node-RED（⭐24k） | 事件驱动可视化编程：节点+连线交互 |
| Activepieces（⭐24k） | AI 工作流平台 |
| organize（⭐3.1k，Python） | 文件整理工具：规则 DSL 设计，可直接读源码 |
| maCrow（Python） | 宏录制回放：可直接读源码 |

## 学习价值（为什么这个项目值得做）

- **Python 后端**：FastAPI、SQLite、多线程、文件系统监控
- **前端**：HTML/CSS/JS、fetch 请求、动态渲染
- **工程思维**：事件驱动架构、防死循环设计、路径规范化（Windows 坑）
- **产品思维**：从「规则管家」一个模块扩展到「自动化工具箱」平台
- **未来衔接**：规则引擎 + AI 理解层 = 你自己的 Agent 管家（与大模型学习方向衔接）
