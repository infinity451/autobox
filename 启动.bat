@echo off
REM ============================================================
REM AutoBox one-click launcher (Windows, dev mode)
REM Double-click to start the server and open the browser.
REM NOTE: pure ASCII on purpose (cmd.exe parses .bat with GBK
REM       on Chinese Windows, Chinese text would be garbled).
REM ============================================================
cd /d "%~dp0"

echo ============================================
echo   AutoBox is starting...
echo   Browser opens automatically in 2 seconds.
echo   Close this window to stop the server.
echo ============================================

start "AutoBox Server" .venv\Scripts\python.exe main.py

timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000
