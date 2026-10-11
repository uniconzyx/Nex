#Requires -Version 5.1
<#
.SYNOPSIS
  构建 Nex 桌面启动器 Nex-Launcher.exe（Windows）。

.DESCRIPTION
  1) 用 Python 创建隔离 venv 并安装 pyinstaller
  2) pyinstaller 按 launcher.spec 打包 deploy/launcher/launcher.py
  3) 产物：deploy/launcher/dist/Nex-Launcher.exe

  纯标准库实现，不打包任何第三方依赖，体积小、可移植。
  运行 .exe 需本机安装 Docker Desktop（用于 docker compose up）。

.EXAMPLE
  pwsh .\build_exe.ps1
#>
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$LauncherDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SpecFile = Join-Path $LauncherDir "launcher.spec"

Write-Host "[build_exe] launcher dir = $LauncherDir"

# 1) venv
$Venv = Join-Path $LauncherDir ".venv"
if (-not (Test-Path $Venv)) {
    Write-Host "[build_exe] 创建 venv: $Venv"
    & $Python -m venv $Venv
}
$Pip = Join-Path $Venv "Scripts/pip.exe"
$Py  = Join-Path $Venv "Scripts/python.exe"

# 2) 安装 pyinstaller
Write-Host "[build_exe] 安装 pyinstaller..."
& $Pip install --upgrade pip | Out-Null
& $Pip install pyinstaller

# 3) 打包
Write-Host "[build_exe] pyinstaller 打包..."
& $Py -m PyInstaller --clean --noconfirm $SpecFile

# 4) 校验
$Exe = Join-Path $LauncherDir "dist/Nex-Launcher.exe"
if (Test-Path $Exe) {
    Write-Host "[build_exe] 成功： $Exe"
    & $Exe --version
} else {
    Write-Error "[build_exe] 未生成 exe，请检查上面的错误。"
    exit 1
}
