@echo off
REM =====================================================================
REM 方案 C：一键开启 Cloudflare Tunnel，把本机 Nex 后端暴露到公网
REM 前提：
REM   1) 已双击 start_backend.cmd 且窗口保持开着（后端在 127.0.0.1:8000）
REM   2) 已安装 cloudflared（winget install cloudflare.cloudflared，或放 PATH）
REM 用法：
REM   双击本文件 -> 终端会吐一个 https://xxxx.trycloudflare.com 临时地址
REM   把它发给助手，由助手跑 rebuild_dist.cmd <该地址> 重编分发版
REM 注意：本窗口必须保持开着；关掉 tunnel 即断，别人连不上
REM =====================================================================
setlocal
cd /d "%~dp0"

where cloudflared >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 cloudflared，请先安装：
    echo   winget install cloudflare.cloudflared
    echo   或下载 https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    echo   把 cloudflared.exe 放进 PATH 后重试。
    pause
    exit /b 1
)

echo ============================================================
echo 正在建立 Cloudflare Tunnel -> http://localhost:8000
echo 请保持本窗口开着；下方出现的 https://xxxx.trycloudflare.com
echo 即为别人可访问的公网地址，发给助手烤进分发版。
echo ============================================================
cloudflared tunnel --url http://localhost:8000
endlocal
