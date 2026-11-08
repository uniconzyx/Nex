@echo off
REM ============================================================================
REM  Nex 后端一键常驻（用于「方案 C：Cloudflare Tunnel 公网暴露」）
REM  由主人本机双击运行；关掉这个窗口即停止后端。
REM   前端/App 通过 Cloudflare Tunnel 把公网请求打回本机 127.0.0.1:8000。
REM   因此本机必须一直开着且此窗口保持运行，别人的电脑才能在线用。
REM ============================================================================
cd /d "%~dp0..\.."

if not exist server\.venv\Scripts\python.exe (
    echo [错误] 未找到 server\.venv\Scripts\python.exe
    echo   请先在 server\ 目录执行：
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Nex 后端将常驻在 http://127.0.0.1:8000
echo 依赖的 postgres / redis 使用已运行的 Docker 容器
echo   ^(cppmind-postgres / cppmind-redis，由 server\docker-compose.yml 起^)
echo.
echo 首次运行若库为空，请另开一个终端执行：
echo   cd server ^&^& .venv\Scripts\python.exe -m scripts.init_db
echo.
echo 保持此窗口打开。关闭窗口即停止后端。
echo ============================================================================
cd server
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
pause
