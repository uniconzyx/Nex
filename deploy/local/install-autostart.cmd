@echo off
chcp 65001 >nul
setlocal
set "ROOT=D:\WB_Workspace\2026-09-19-21-42-03\CppMind"
echo Registering Nex local service to start at logon...
schtasks /create /tn "Nex Local Server" /tr "\"%ROOT%\server\.venv\Scripts\pythonw.exe\" \"%ROOT%\deploy\local\nex_local_server.py\"" /sc onlogon /rl limited /f
if errorlevel 1 (echo FAILED. Run this as administrator or start manually with Nex.cmd) else (echo OK. Nex will be available at http://127.0.0.1:8000/ after next logon)
pause
