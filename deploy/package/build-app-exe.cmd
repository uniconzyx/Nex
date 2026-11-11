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
copy /y "target\x86_64-pc-windows-gnu\release\nex.exe" "..\release\nex-shell\Nex.exe" >nul
if exist "target\x86_64-pc-windows-gnu\release\WebView2Loader.dll" copy /y "target\x86_64-pc-windows-gnu\release\WebView2Loader.dll" "..\release\nex-shell\" >nul
REM 桌面判题资源：Rust detect_go_judge() 只认 EXE 同级 binaries/go-judge.exe
if not exist "..\release\nex-shell\binaries" mkdir "..\release\nex-shell\binaries"
if not exist "binaries\go-judge.exe" echo [nex-app] ERROR: src-tauri/binaries/go-judge.exe missing & exit /b 1
copy /y "binaries\go-judge.exe" "..\release\nex-shell\binaries\go-judge.exe" >nul
if errorlevel 1 exit /b 1
echo [nex-app] EXE ready: release\nex-shell\Nex.exe
