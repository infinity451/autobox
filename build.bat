@echo off
REM ============================================================
REM AutoBox build script (Windows)
REM Double-click to build AutoBox.exe into dist/
REM Result: dist\AutoBox.exe - a DESKTOP app (native window,
REM         no browser tab). Double-click to run.
REM
REM NOTE:
REM  - Pure ASCII on purpose: cmd.exe parses .bat with the system
REM    codepage (GBK on Chinese Windows), Chinese would garble.
REM  - Entry is desktop.py (native window via pywebview).
REM  - First run of the exe creates a data folder beside it.
REM ============================================================

cd /d "%~dp0"

echo ============================================
echo   Building AutoBox (desktop app), 1-3 min...
echo   Output: dist\AutoBox.exe
echo ============================================

.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --noconsole --name AutoBox ^
  --add-data "static;static" ^
  --collect-all playwright ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import webview.platforms.edgechromium ^
  desktop.py

if exist "dist\AutoBox.exe" (
  echo.
  echo ============================================
  echo   BUILD OK: dist\AutoBox.exe
  echo   Double-click to open the desktop window
  echo ============================================
) else (
  echo.
  echo   BUILD FAILED, check messages above
)
