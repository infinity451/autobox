# AutoBox 自动化工具箱

> 一个本地运行的「如果…就…」自动化平台：规则管家自动处理文件、网页采集器抓取数据、
> 批量文件魔法处理杂事、宏录制器回放操作、定时提醒中心定时关机。
> **数据全部存在本机，不上传云端。**

## 现在能用什么

**📁 规则管家**（第 1 阶段）：创建「如果…就…」规则，自动处理文件。
- 触发器：有新文件出现 / 文件被修改 / 定时触发（cron）
- 条件：文件名包含 / 扩展名属于 / 大小大于小于（可多条件，全部满足才执行）
- 动作：移动 / 复制 / 重命名 / 通知（按顺序执行，支持 `{{file.name}}` 模板变量）

**🕸️ 网页采集器**（第 2 阶段）：配置式爬虫——填网址 + CSS 选择器，一键采集到 CSV。
- 列表容器选择器 + 多字段提取（文本/链接/图片地址/HTML）
- 支持定时自动采集（cron），结果导出 CSV（Excel 直接打开不乱码）
- 内置本地测试页 `static/test_page.html` 练手（不依赖外网）

**🪄 批量文件魔法**（第 3 阶段）：批量重命名（加前缀/后缀/替换/序号），先预览后执行。
- 冲突自动检测（撞名/目标已存在会跳过，绝不覆盖）
- 单个文件失败不影响其他

**⏰ 定时提醒中心**（第 3 阶段）：到点自动做事。
- 弹窗提醒（Windows 系统消息框，无第三方依赖）
- 定时关机 / 重启（60 秒缓冲可反悔）/ 休眠
- 定时打开程序

**🎬 宏录制器**（第 4 阶段）：录操作 → 一键回放。
- 录制鼠标键盘操作（移动/点击/滚动/打字），保存为宏
- 回放支持速度控制（1x/2x/4x），**按 F8 紧急停止**
- 播放前强确认（回放会真的操作电脑，安全第一）

**五个模块全部完成！**

## 快速开始

```bash
# 1.（首次）创建虚拟环境并安装依赖（项目根目录执行）
python -m venv .venv                # 创建干净环境（隔离系统 Python）
.venv\Scripts\python -m pip install -r requirements.txt   # 在 venv 里装依赖

# 2. 启动（用 venv 里的 Python，别用系统 Python）
.venv\Scripts\python main.py

# 3. 浏览器打开
http://127.0.0.1:8000
```

**或者**：直接双击根目录的 `启动.bat`——自动用 venv 启动服务并打开浏览器（一键启动，以后都这么用）。

## 打包成桌面应用 exe（发给身边的人用）

AutoBox 是**真正的桌面应用**：双击 exe 弹出**独立原生窗口**（不是浏览器标签页），关窗即退出。

```bash
# 打包（双击 build.bat 或运行下面的命令，入口是 desktop.py）
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --name AutoBox ^
  --add-data "static;static" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import webview.platforms.edgechromium ^
  desktop.py

# 产物：dist\AutoBox.exe（约 23MB 单文件）
```

**使用方法**：把 `AutoBox.exe` 发给别人（微信/QQ 传文件），对方**双击即用**——弹出 AutoBox 窗口（用系统 WebView2 引擎，Win10/11 自带），关窗即停止。

**两种运行模式**：
- `desktop.py` / 打包的 exe：**桌面窗口模式**（默认，推荐给用户）
- `main.py`：网页模式（开发调试用，浏览器访问 http://127.0.0.1:8000）

**注意事项**：
- 首次运行会在 exe **旁边**自动创建 `data` 文件夹（用户数据都在里面，备份/迁移就复制这个文件夹）
- 杀毒软件可能误报（PyInstaller 打包的常见现象）：添加信任即可，源码全在仓库里可自查
- 系统需有 WebView2 Runtime（Win10/11 一般自带；老系统可到微软官网安装）

### 桌面模式实现原理（一句话）

后台线程启动本地网页服务（uvicorn）+ pywebview 开原生窗口加载它；
窗口关闭时优雅停止服务（`window.events.closing` 事件），数据全部在本机。

### 为什么用虚拟环境（venv）？

- 每个项目的依赖**装在自己项目的 .venv 里**，互不干扰（你电脑上有 4 个 Python，混装容易出"装了库却 import 不到"的坑）
- 系统 Python 保持干净，venv 坏了删掉 `.venv` 文件夹重建即可，不影响任何东西
- 更新依赖：`pip install -r requirements.txt`（在 venv 激活状态下或直接用 `.venv\Scripts\python -m pip`）

想立刻体验：网页 → 规则管家 → 新建规则，监控目录填 `D:/Learn/autobox/data/test_download`，
动作「移动」目标填 `D:/Learn/autobox/data/test_moved`，然后往 test_download 丢一个 .txt 文件，
几秒后看日志和 test_moved 目录——文件被自动移动了。

## 项目结构（每个文件夹都有 README 说明）

```
autobox/
├─ README.md                ← 本文件：项目总览
├─ requirements.txt         ← 依赖清单（pip install 安装）
├─ main.py                  ← 网页模式入口（python main.py，开发调试用）
├─ desktop.py               ← 桌面模式入口（原生窗口，打包 exe 用）
├─ build.bat                ← 打包脚本（生成 dist\AutoBox.exe 桌面应用）
├─ 启动.bat                 ← 开发模式一键启动（双击即用）
├─ fetch_github.py          ← 工具脚本：搜 GitHub 同类项目（研究用）
├─ fetch_repos.py           ← 工具脚本：查知名开源项目详情（研究用）
├─ app/                     ← 后端（Python）
│  ├─ README.md             ← app 目录说明
│  ├─ __init__.py           ← 包身份证
│  ├─ paths.py              ← 统一路径工具（开发/打包双模式）
│  ├─ database.py           ← 数据层：SQLite 建表/读写/日志
│  ├─ models.py             ← 规则模型：触发器/条件/动作定义与校验
│  ├─ api.py                ← 接口层：网页请求 ↔ Python 调用
│  ├─ engine/               ← 自动化引擎（心脏）
│  │  ├─ README.md          ← engine 目录说明
│  │  ├─ __init__.py        ← 包身份证
│  │  ├─ rules.py           ← 规则管理：增删改查
│  │  ├─ matcher.py         ← 条件匹配：文件满不满足条件
│  │  ├─ actions.py         ← 动作执行：移动/复制/重命名/通知
│  │  ├─ triggers.py        ← 触发器：文件监控(watchdog) + 定时(APScheduler)
│  │  └─ scheduler.py       ← 引擎主控：串起全链路 + 防死循环
│  └─ crawler/              ← 网页采集器（第 2 阶段）
│     ├─ README.md          ← crawler 目录说明
│     ├─ __init__.py        ← 包身份证
│     ├─ tasks.py           ← 采集任务管理：增删改查
│     ├─ fetcher.py         ← 抓取解析：requests + BeautifulSoup
│     └─ runner.py          ← 执行器：跑采集 + 导出 CSV + 定时
│  ├─ batch/                ← 批量文件魔法（第 3 阶段）
│  │  ├─ README.md          ← batch 目录说明
│  │  ├─ __init__.py        ← 包身份证
│  │  └─ rename.py          ← 批量重命名引擎（预览+执行）
│  ├─ timer/                ← 定时提醒中心（第 3 阶段）
│  │  ├─ README.md          ← timer 目录说明
│  │  ├─ __init__.py        ← 包身份证
│  │  ├─ tasks.py           ← 定时任务管理：增删改查
│  │  └─ runner.py          ← 执行器：弹窗/关机/打开程序 + 定时调度
│  └─ macro/                ← 宏录制器（第 4 阶段）
│     ├─ README.md          ← macro 目录说明
│     ├─ __init__.py        ← 包身份证
│     ├─ store.py           ← 宏存储：增删改查
│     ├─ recorder.py        ← 录制器：pynput 监听鼠标键盘
│     └─ player.py          ← 回放器：pynput 重放 + 速度控制 + F8 停止
├─ static/                  ← 前端（网页）
│  ├─ README.md             ← static 目录说明
│  ├─ index.html            ← 首页·功能中心
│  ├─ rules.html            ← 规则管家页面
│  ├─ crawler.html          ← 网页采集器页面
│  ├─ batch.html            ← 批量文件魔法页面
│  ├─ timer.html            ← 定时提醒中心页面
│  ├─ test_page.html        ← 采集器本地测试页（模拟新闻站）
│  ├─ css/
│  │  ├─ README.md          ← css 目录说明
│  │  └─ style.css          ← 全局样式
│  └─ js/
│     ├─ README.md          ← js 目录说明
│     ├─ api.js             ← 请求后端接口的工具函数
│     ├─ index.js           ← 首页脚本
│     ├─ rules.js           ← 规则管家脚本
│     ├─ crawler.js         ← 采集器脚本
│     ├─ batch.js           ← 批量文件魔法脚本
│     └─ timer.js           ← 定时提醒中心脚本
└─ data/                    ← 数据（自动生成）
   ├─ README.md             ← data 目录说明
   ├─ autobox.db            ← 主数据库（规则/任务/日志）
   ├─ exports/              ← 采集器导出的 CSV 文件
   ├─ test_download/        ← 测试用模拟下载目录
   ├─ test_moved/           ← 测试用模拟目标目录
   └─ test_batch/           ← 测试用批量重命名目录
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
| 2 | 网页采集器（配置式爬虫 → CSV，含定时，参考 EasySpider 交互） | ✅ 完成（可跑通） |
| 3 | 批量文件魔法 + 定时提醒中心（含定时关机） | ✅ 完成（可跑通） |
| 4 | 宏录制器（参考 maCrow，pynput） | ✅ 完成（可跑通） |
| 5 | 打包 exe（PyInstaller）+ 路径统一 + 自动开浏览器 + 优雅退出 | ✅ 完成（dist\AutoBox.exe 已验证可运行） |
| 后续 | 网页变化触发器（参考 Huginn 事件模型）、规则联动（参考 n8n 节点理念）、通知模块接 Apprise 库 | 规划中 |
| 优化 | 用户问题清单 7 项（补单测/_busy 清理/refresh 增量/目录校验/定时规则校验/版本管理——优雅退出已在第 5 阶段顺带解决） | 待优化阶段 |

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
