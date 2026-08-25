@echo off
REM ============================================================
REM AutoBox 一键启动脚本（Windows）
REM 双击本文件即可启动 AutoBox，并自动打开浏览器。
REM 原理：
REM   1. 用虚拟环境里的 python 启动 main.py（依赖都在 .venv 里）
REM   2. 等 2 秒让服务起来，然后调用系统默认浏览器打开网页
REM ============================================================

REM 关闭回显后，命令执行时不再打印命令本身（界面干净）
@echo off
REM 切换到脚本所在的目录（保证 python main.py 找得到项目文件）
cd /d "%~dp0"

REM 显示提示
echo ============================================
echo   AutoBox 自动化工具箱 正在启动...
echo   启动后会自动打开浏览器，关闭本窗口=停止服务
echo ============================================

REM 启动服务器（用虚拟环境的 python，不污染系统环境）
REM start "窗口标题" 命令  = 新开一个窗口运行，防止本窗口被占住
start "AutoBox Server" .venv\Scripts\python.exe main.py

REM 等 2 秒，让服务器先跑起来（不然浏览器会打不开页面）
timeout /t 2 /nobreak >nul

REM 用系统默认浏览器打开 AutoBox 首页
start http://127.0.0.1:8000

REM 脚本结束
