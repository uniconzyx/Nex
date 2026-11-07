@echo off
REM 出 Windows 原生 EXE（内嵌 web-preview 桌面版 UI）
cd /d "%~dp0..\..\src-tauri"
set NO_PROXY=*
set no_proxy=*
REM 必须显式 --target：.cargo/config.toml 只配 rustflags，未设默认 target
call "..\frontend\node_modules\.bin\tauri.cmd" build --no-bundle --target x86_64-pc-windows-gnu --config tauri.shell.desktop.conf.json
if errorlevel 1 exit /b 1
if not exist "..\release\nex-shell" mkdir "..\release\nex-shell"
copy /y "target\x86_64-pc-windows-gnu\release\nex.exe" "..\release\nex-shell\Nex-Desktop-1.0.exe" >nul
if exist "target\x86_64-pc-windows-gnu\release\WebView2Loader.dll" copy /y "target\x86_64-pc-windows-gnu\release\WebView2Loader.dll" "..\release\nex-shell\" >nul
echo [nex-shell] EXE ready in release\nex-shell
