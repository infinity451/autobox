@echo off
REM ============================================================
REM AutoBox build script (Windows)
REM Double-click to build AutoBox.exe into dist/
REM Result: dist\AutoBox.exe  (single file, double-click to run)
REM
REM NOTE:
REM  - This file is pure ASCII on purpose: cmd.exe parses batch
REM    files with the system codepage (GBK on Chinese Windows),
REM    so Chinese text in .bat files turns into garbage.
REM  - First run of the exe creates a data folder beside it.
REM ============================================================

cd /d "%~dp0"

echo ============================================
echo   Building AutoBox, wait 1-3 minutes...
echo   Output: dist\AutoBox.exe
echo ============================================

.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --name AutoBox ^
  --add-data "static;static" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan.on ^
  main.py

if exist "dist\AutoBox.exe" (
  echo.
  echo ============================================
  echo   BUILD OK: dist\AutoBox.exe
  echo   Double-click to run, browser opens automatically
  echo ============================================
) else (
  echo.
  echo   BUILD FAILED, check messages above
)
