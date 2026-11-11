@echo off
REM ============================================================
REM  Canteen booking system launcher
REM  Python detection order:
REM    1) WorkBuddy bundled Python (project deps already installed)
REM    2) Any working python on PATH (skips Microsoft Store stub)
REM ============================================================
setlocal
set "PYTHONUTF8=1"
set "PY="

REM 1) WorkBuddy bundled Python
for /d %%G in ("C:\Users\it_zzy\.workbuddy\binaries\python\versions\*") do if exist "%%G\python.exe" set "PY=%%G\python.exe"

REM 2) Fallback: working python on PATH
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do call :try_python "%%~P"

if not defined PY (
  echo.
  echo [ERROR] Python not found.
  echo         Install Python 3.13 and add it to PATH, then run this file again.
  pause
  exit /b 1
)

echo Using Python: %PY%
cd /d "%~dp0backend"
"%PY%" -m uvicorn main:app --host 0.0.0.0 --port 8000
endlocal
exit /b 0

:try_python
if defined PY exit /b 0
echo %~1| find /i "WindowsApps" >nul && exit /b 0
"%~1" -c "import sys" >nul 2>nul && set "PY=%~1"
exit /b 0
