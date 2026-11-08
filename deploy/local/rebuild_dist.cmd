@echo off
REM ============================================================================
REM  用指定「线上后端地址」重建前端分发产物（deploy/package/app）
REM  用法:
REM    rebuild_dist.cmd https://xxxx.trycloudflare.com
REM    rebuild_dist.cmd https://nex.你的域名.com
REM  该地址会被烤进 EXE/APK 的默认后端，装到别人电脑上默认就连这个线上服务。
REM  重建完再双击 deploy\package\build-app-exe.cmd / build-app-apk.cmd 重编双端包。
REM ============================================================================
if "%1"=="" (
    echo 用法: rebuild_dist.cmd ^<线上后端地址^>
    echo   例: rebuild_dist.cmd https://xxxx.trycloudflare.com
    echo   例: rebuild_dist.cmd https://nex.你的域名.com
    pause
    exit /b 1
)

cd /d "%~dp0..\.."
set "NEX_API_BASE=%1"

where python >nul 2>&1 || (
    echo [错误] 未找到 python，请安装 Python 3.11+ 并加入 PATH
    pause
    exit /b 1
)

echo 用后端地址 %NEX_API_BASE% 重建前端分发产物...
python deploy/package/prepare_app.py
if errorlevel 1 (
    echo [失败] prepare_app.py 报错，详见上方输出
    pause
    exit /b 1
)

echo.
echo 前端已重建到 deploy/package/app （默认后端 = %NEX_API_BASE%）
echo 接着请双击:
echo   deploy\package\build-app-exe.cmd   重编桌面 EXE
echo   deploy\package\build-app-apk.cmd   重编安卓 APK
echo （重编会再次触发 prepare_app，地址保持一致）
pause
