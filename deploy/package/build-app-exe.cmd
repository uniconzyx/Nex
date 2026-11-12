@echo off
REM Nex 真应用 Windows EXE（单文件，不需要 WebView2Loader.dll）
REM 由 deploy/package/prepare_app.py 生成，请改生成器而不是改本文件
REM 必须用 msvc 工具链：webview2-com-sys 只在 target_env=msvc 时静态链接
REM WebView2LoaderStatic.lib；gnu 工具链退化成动态加载 WebView2Loader.dll。
cd /d "%~dp0..\..\src-tauri"
set NO_PROXY=*
set no_proxy=*
REM vcvars64 提供 MSVC link.exe / LIB / INCLUDE，须在追加 PATH 之前调用
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "MSVC_BIN=C:\Users\zyx\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin"
set "PATH=%MSVC_BIN%;%PATH%"
set "RUSTUP_TOOLCHAIN=stable-x86_64-pc-windows-msvc"
REM 必须显式 --target：.cargo/config.toml 只配 rustflags，未设默认 target
call "..\frontend\node_modules\.bin\tauri.cmd" build --no-bundle --target x86_64-pc-windows-msvc --config tauri.app.desktop.conf.json
if errorlevel 1 exit /b 1
if not exist "..\release\nex-shell" mkdir "..\release\nex-shell"
copy /y "target\x86_64-pc-windows-msvc\release\nex.exe" "..\release\nex-shell\Nex.exe" >nul
if errorlevel 1 exit /b 1
REM 关键：MSVC 产物不带 Win32 manifest，缺它会在加载阶段直接 0xC0000139 退出
REM （无 WER 记录、无日志、无 stderr，极难定位）。注入与 gnu 版同源的 manifest。
"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\mt.exe" -manifest "..\deploy\package\nex.manifest.xml" "-outputresource:..\release\nex-shell\Nex.exe;#1"
if errorlevel 1 echo [nex-app] ERROR: manifest injection failed & exit /b 1
REM 桌面判题资源：Rust detect_go_judge() 只认 EXE 同级 binaries/go-judge.exe
if not exist "..\release\nex-shell\binaries" mkdir "..\release\nex-shell\binaries"
if not exist "binaries\go-judge.exe" echo [nex-app] ERROR: src-tauri/binaries/go-judge.exe missing & exit /b 1
copy /y "binaries\go-judge.exe" "..\release\nex-shell\binaries\go-judge.exe" >nul
if errorlevel 1 exit /b 1
echo [nex-app] EXE ready: release\nex-shell\Nex.exe
