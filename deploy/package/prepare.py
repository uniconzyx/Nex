#!/usr/bin/env python3
"""Nex 双端原生封装 · 准备阶段（幂等，可反复执行）。

把 web-preview/ 的两套 UI 各制备成一份自包含静态站，并生成两份 Tauri
增量配置（--config 合并，不改动默认 tauri.conf.json / dist / frontend）。

    deploy/package/desktop/index.html  <- kaimao-desktop.html
    deploy/package/mobile/index.html   <- kaimao-mobile.html
    src-tauri/tauri.shell.desktop.conf.json
    src-tauri/tauri.shell.mobile.conf.json

之后用 deploy/package/build-exe.cmd / build-apk.cmd 出包。
"""
from __future__ import annotations

import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
WEB = ROOT / "web-preview"
PKG = ROOT / "deploy" / "package"
TAURI = ROOT / "src-tauri"

# 只搬运行期真正会用到的资源；设计检查截图 / 源图 / 工具脚本不进包。
TOP_FILES = [
    "favicon-64.png",
    "maine_coon.png",
    "maine_coon_avatar.png",
    "maine_coon_blue.png",
]
ASSET_SKIP_DIRS = {"kaimao-src"}
ASSET_SKIP_FILES = {"preview-sheet.png"}

CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "   # 两端 HTML 含内联 <script>，必须放行
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "connect-src 'self' ipc: http: https: ws: wss: data: blob:"
)


def stage(kind: str, src_name: str) -> int:
    out = PKG / kind
    out.mkdir(parents=True, exist_ok=True)

    # index.html = 对应端页面；Tauri 固定以 index.html 为入口
    shutil.copyfile(WEB / src_name, out / "index.html")

    for name in TOP_FILES:
        p = WEB / name
        if p.is_file():
            shutil.copyfile(p, out / name)

    assets_out = out / "assets"
    assets_out.mkdir(exist_ok=True)
    src_assets = WEB / "assets"
    for p in src_assets.rglob("*"):
        rel = p.relative_to(src_assets)
        if any(part in ASSET_SKIP_DIRS for part in rel.parts):
            continue
        if p.is_dir():
            (assets_out / rel).mkdir(parents=True, exist_ok=True)
            continue
        if p.name in ASSET_SKIP_FILES:
            continue
        dst = assets_out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst)

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    count = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"[prepare] {kind}: {count} files, {total / 1024 / 1024:.2f} MB -> {out}")
    return count


def write_conf(name: str, kind: str, title: str | None) -> None:
    conf: dict = {
        "build": {
            "frontendDist": f"../deploy/package/{kind}",
            # 跳过默认配置里的 React `npm run build`：封装包用的是 web-preview，
            # 重新构建 React 既无必要也会污染 dist/。
            "beforeBuildCommand": None,
            "beforeDevCommand": None,
        },
        "app": {
            "security": {"csp": CSP},
        },
    }
    if title:
        conf["app"]["windows"] = [{
            "label": "main",
            "title": title,
            "width": 1280,
            "height": 820,
            "minWidth": 900,
            "minHeight": 640,
            "resizable": True,
            "fullscreen": False,
            "center": True,
        }]
    path = TAURI / name
    path.write_text(json.dumps(conf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[prepare] config -> {path}")


def write_cmd(name: str, lines: list[str]) -> None:
    path = PKG / name
    with path.open("w", encoding="gbk", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[prepare] script -> {path}")


def main() -> None:
    stage("desktop", "kaimao-desktop.html")
    stage("mobile", "kaimao-mobile.html")
    write_conf("tauri.shell.desktop.conf.json", "desktop", "Nex · 桌面版")
    write_conf("tauri.shell.mobile.conf.json", "mobile", None)

    write_cmd("build-exe.cmd", [
        "@echo off",
        "REM 出 Windows 原生 EXE（内嵌 web-preview 桌面版 UI）",
        "cd /d \"%~dp0..\\..\\src-tauri\"",
        "set NO_PROXY=*",
        "set no_proxy=*",
        "call \"..\\frontend\\node_modules\\.bin\\tauri.cmd\" build --no-bundle --config tauri.shell.desktop.conf.json",
        "if errorlevel 1 exit /b 1",
        "if not exist \"..\\release\\nex-shell\" mkdir \"..\\release\\nex-shell\"",
        "copy /y \"target\\x86_64-pc-windows-gnu\\release\\nex.exe\" \"..\\release\\nex-shell\\Nex-Desktop-1.0.exe\" >nul",
        "if exist \"target\\x86_64-pc-windows-gnu\\release\\WebView2Loader.dll\" copy /y \"target\\x86_64-pc-windows-gnu\\release\\WebView2Loader.dll\" \"..\\release\\nex-shell\\\" >nul",
        "echo [nex-shell] EXE ready in release\\nex-shell",
    ])
    write_cmd("build-apk.cmd", [
        "@echo off",
        "REM 出 Android arm64 APK（内嵌 web-preview 竖屏版 UI）",
        "cd /d \"%~dp0..\\..\\src-tauri\"",
        "set NO_PROXY=*",
        "set no_proxy=*",
        "set ANDROID_HOME=D:\\Sdk",
        "set ANDROID_SDK_ROOT=D:\\Sdk",
        "set NDK_HOME=D:\\Sdk\\ndk\\android-ndk-r27c",
        "set JAVA_HOME=C:\\Program Files\\Java\\jdk-23",
        "set CI=true",
        "call \"..\\frontend\\node_modules\\.bin\\tauri.cmd\" android build --apk --target aarch64 --split-per-abi --config tauri.shell.mobile.conf.json",
        "REM Windows 未开开发者模式时，末尾「创建符号链接」报错属预期，.so 已生成",
        "if not exist \"target\\aarch64-linux-android\\release\\libnex.so\" exit /b 1",
        "if not exist \"gen\\android\\app\\src\\main\\jniLibs\\arm64-v8a\" mkdir \"gen\\android\\app\\src\\main\\jniLibs\\arm64-v8a\"",
        "copy /y \"target\\aarch64-linux-android\\release\\libnex.so\" \"gen\\android\\app\\src\\main\\jniLibs\\arm64-v8a\\libnex.so\" >nul",
        "cd /d \"gen\\android\"",
        "call gradlew.bat assembleRelease --no-daemon -x rustBuildArm64Release -x rustBuildArmRelease -x rustBuildX86Release -x rustBuildX86_64Release",
        "if errorlevel 1 exit /b 1",
        "if not exist \"..\\..\\..\\release\\nex-shell\" mkdir \"..\\..\\..\\release\\nex-shell\"",
        "\"D:\\Sdk\\build-tools\\35.0.0\\zipalign.exe\" -f -p 4 app\\build\\outputs\\apk\\arm64\\release\\app-arm64-release-unsigned.apk \"..\\..\\..\\release\\nex-shell\\tmp.apk\"",
        "call \"D:\\Sdk\\build-tools\\35.0.0\\apksigner.bat\" sign --ks keystore\\nex-release.jks --ks-pass pass:nex2026 --key-pass pass:nex2026 --ks-key-alias nex --out \"..\\..\\..\\release\\nex-shell\\Nex-Mobile-1.0-arm64.apk\" \"..\\..\\..\\release\\nex-shell\\tmp.apk\"",
        "del \"..\\..\\..\\release\\nex-shell\\tmp.apk\"",
        "echo [nex-shell] APK ready in release\\nex-shell",
    ])
    print("[prepare] done")


if __name__ == "__main__":
    main()
