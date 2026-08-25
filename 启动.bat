@echo off
REM ============================================================
REM AutoBox launcher (Windows, dev mode)
REM Double-click to open the AutoBox desktop window.
REM NOTE: pure ASCII on purpose (cmd.exe parses .bat with GBK
REM       on Chinese Windows, Chinese text would be garbled).
REM ============================================================
cd /d "%~dp0"

echo ============================================
echo   AutoBox is starting...
echo   Close the AutoBox window to stop it.
echo ============================================

.venv\Scripts\python.exe desktop.py
