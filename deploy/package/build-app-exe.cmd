@echo off
REM Nex 真应用 Windows EXE（内嵌 frontend React 应用）
REM 由 deploy/package/prepare_app.py 生成，请改生成器而不是改本文件
cd /d "%~dp0..\..\src-tauri"
set NO_PROXY=*
set no_proxy=*
REM 必须显式 --target：.cargo/config.toml 只配 rustflags，未设默认 target
call "..\frontend\node_modules\.bin\tauri.cmd" build --no-bundle --target x86_64-pc-windows-gnu --config tauri.app.desktop.conf.json
if errorlevel 1 exit /b 1
if not exist "..\release\nex-shell" mkdir "..\release\nex-shell"
copy /y "target\x86_64-pc-windows-gnu\release\nex.exe" "..\release\nex-shell\Nex-App-Desktop-1.0.exe" >nul
if exist "target\x86_64-pc-windows-gnu\release\WebView2Loader.dll" copy /y "target\x86_64-pc-windows-gnu\release\WebView2Loader.dll" "..\release\nex-shell\" >nul
echo [nex-app] EXE ready: release\nex-shell\Nex-App-Desktop-1.0.exe
