@echo off
chcp 65001 >nul
schtasks /delete /tn "Nex Local Server" /f
pause
