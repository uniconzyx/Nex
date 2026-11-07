@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
if "%~1"=="" (set "NEX_MODE=desktop") else (set "NEX_MODE=%~1")
"server\.venv\Scripts\python.exe" "deploy\local\daemon.py" start
if errorlevel 1 goto fail
"server\.venv\Scripts\python.exe" "deploy\local\daemon.py" open %NEX_MODE%
exit /b 0
:fail
echo [Nex] Failed to start. Check D:\WB_Workspace\_nex_local\server.log
pause
exit /b 1
