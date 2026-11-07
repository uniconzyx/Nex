@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0..\.."
"server\.venv\Scripts\python.exe" "deploy\local\daemon.py" stop
pause
