# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 规格（one-file 控制台版，纯标准库，体积小、可移植）
# 构建：pyinstaller launcher.spec  ->  dist/Nex-Launcher.exe

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],                           # binaries list
    name="Nex-Launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,               # 保留控制台显示启动日志；改为 False 可隐藏窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="nex.ico",             # Nex 应用图标（由源图生成）
)
