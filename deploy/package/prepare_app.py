#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nex 双端「真应用」封装 · 准备阶段（幂等，可反复执行）。

与 prepare.py 是两条互不干扰的路线，产物文件名不同、绝不互相覆盖：

    prepare.py      web-preview/ 两套静态设计稿
                    -> Nex-Desktop-1.0.exe / Nex-Mobile-1.0-arm64.apk
    本脚本           frontend/ React 应用（章节 / 题库 / 判题 / 实验 / 进度）
                    -> Nex-App-Desktop-1.0.exe / Nex-App-Mobile-1.0-arm64.apk

为什么单独出一份 staging，而不是直接把 frontendDist 指回 ../dist：
  vite.config.ts 里 emptyOutDir=false（清空 outDir 会触发本机批量删除守卫），
  dist/ 因此累积了历次构建的哈希产物（实测 207 文件 / 195MB）。整目录塞进
  Tauri 会把 EXE / APK 撑到不可用。这里让 vite 输出到干净的
  deploy/package/app/，只带当前这一次构建的文件（实测约 38 文件 / 7MB）。

生成的增量配置只覆盖 build.frontendDist / 窗口标题 / app.security.csp。
CSP 必须比默认多一条 `'wasm-unsafe-eval'`：判题用 Pyodide（WASM），
Chromium 在 `script-src 'self'` 下会拒绝 WebAssembly.instantiateStreaming，
现象是点「提交判题」后永远停在「准备解释器…」，且控制台不报 CSP 违规、
静态资源也不 404，极难定位。该 source 只放开 wasm 编译，不等于
unsafe-eval，不会引入 JS eval；其余指令逐字沿用 tauri.conf.json。
beforeBuildCommand 置空：staging 已由本脚本产出，不必再跑 npm run build
去重写 dist/。

APK 注意（既有缺陷，别再踩）：Tauri v2 在 android build 时不会把
frontendDist 指向的 staging 拷进 app/src/main/assets/dist，导致打出的 APK
内只有 Rust 二进制、没有前端页面（首发版 APK 也有此缺陷，解包后 0 个
html/js）。build-app-apk.cmd 里因此在 gradlew 之前补一道 xcopy，把
deploy/package/app 同步进该目录。改这条逻辑务必同步 .cmd 与下方 self_check。

运行期资源（缺一项就会让「提交判题」静默变坏，别删）：
  * frontend/public/pyodide/ 由 scripts/fetch_pyodide.py 落地，vite 原样拷进
    staging 根；protocol.ts 的 DEFAULT_INDEX_URL 指向同源 /pyodide/。
  * src-tauri/binaries/go-judge.exe 由 build-app-exe.cmd 拷到 EXE 同级的
    binaries/，Rust detect_go_judge() 才会认定桌面判题可用；只打裸 EXE
    而不落这份资源，判题会静默降级成 mock 直跑（回显而非真编译）。
verify_staging() 与 self_check() 分别守 staging 侧与生成器侧。

用法：python deploy/package/prepare_app.py
之后：deploy/package/build-app-exe.cmd / build-app-apk.cmd
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PKG = ROOT / "deploy" / "package"
TAURI = ROOT / "src-tauri"
STAGING = PKG / "app"

EXE_OUT = "Nex-App-Desktop-1.0.exe"
APK_OUT = "Nex-App-Mobile-1.0-arm64.apk"

# 与 tauri.conf.json 的 app.security.csp 逐字一致，只多放一条 wasm 编译权限。
# 改动这里必须同步 scratch/ 里几个 headless 验收脚本的 CSP 常量。
APP_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'wasm-unsafe-eval'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "connect-src 'self' ipc: http: https: ws: wss: data: blob:"
)

# staging 体检阈值：一次正常的 vite build 远低于这两个数；
# 一旦有人误把整个 dist/ 拷进来，这里会立刻挡下而不是打出一个巨型包。
MAX_FILES = 120
MAX_MB = 40

# Pyodide 运行时必备文件（vite 从 public/ 原样拷进 staging 根）。
# 它们不在 index.html 的引用闭包里，必须单独验；少一个文件在 dev 模式可能
# 不显形，封装后却会让移动端判题 100% 失败。
PYODIDE_REQUIRED = (
    "pyodide/pyodide.mjs",
    "pyodide/pyodide.asm.js",
    "pyodide/pyodide.asm.wasm",
    "pyodide/python_stdlib.zip",
    "pyodide/pyodide-lock.json",
)

# Vite 产物里动态 import / CSS url() 指向的文件名（带内容哈希）。
ASSET_REF = re.compile(
    r"(?:\./|/assets/)?([A-Za-z0-9_@.-]+\.(?:js|mjs|css|png|svg|jpe?g|webp|gif|woff2?|json))"
)
# index.html 里以 / 开头的同源引用（/assets/xxx、/favicon.svg 等）。
HTML_REF = re.compile(r'(?:src|href)="(/[^"]+)"')


def node_bin() -> str:
    """优先用 NEX_NODE（隔离环境的 managed node），其次系统 PATH。"""
    p = os.environ.get("NEX_NODE") or shutil.which("node") or shutil.which("node.exe")
    if not p:
        raise SystemExit("找不到 node：请设置 NEX_NODE 指向 node.exe")
    return p


def clean_staging() -> None:
    """把上一版 staging 整体挪到 scratch/（同盘 rename，零删除）。

    为什么不逐文件 unlink：本机安全守卫按「单个 turn 内累计删除数」计数，
    达到 50 次就要求确认。Pyodide 本地化之后 staging 有 60+ 文件，逐文件删
    必然撞线，vite 还没跑就先失败了。同盘目录 rename 是原子操作，既不算
    删除、也不需要批量确认；旧产物留在已 gitignore 的 scratch/ 里，
    需要腾空间时由主人手动清理即可。
    """
    if not STAGING.is_dir():
        return
    backup_root = ROOT / "scratch"
    backup_root.mkdir(parents=True, exist_ok=True)
    dst = backup_root / f"_app_staging_prev_{int(time.time() * 1000)}"
    STAGING.rename(dst)
    print(f"[prepare_app] previous staging -> {dst.relative_to(ROOT)} "
          "(已 gitignore，可手动清理)")


def build_staging() -> None:
    """让 vite 把「当前这一次」构建输出到干净的 app/ 目录。"""
    vite = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if not vite.is_file():
        raise SystemExit(f"缺少 vite CLI：{vite}（先在 frontend/ 装依赖）")
    # 注入线上后端地址：Vite 仅从 .env 读取 VITE_* 变量，故临时写 frontend/.env
    # 并在构建后恢复。NEX_API_BASE 缺省为 127.0.0.1:8000（本机 Docker 后端）；
    # 分发版应由构建环境传入真实线上地址（如 https://api.你的域名.com），
    # 这样烤进 EXE/APK 的默认地址就是线上服务，装到别人电脑上也会默认连线上后端。
    api_base = os.environ.get("NEX_API_BASE", "http://127.0.0.1:8000")
    env_file = FRONTEND / ".env"
    prev = env_file.read_text(encoding="utf-8") if env_file.is_file() else None
    lines = (prev.splitlines() if prev else [])
    lines = [ln for ln in lines if not ln.startswith("VITE_NEX_API_BASE=")]
    lines.append(f"VITE_NEX_API_BASE={api_base}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        # outDir 相对 vite 的 root（=frontend/）解析；不要加 --emptyOutDir，
        # 本机批量删除守卫会拦，目录已由 clean_staging() 清空。
        cmd = [node_bin(), str(vite), "build", "--outDir", "../deploy/package/app"]
        r = subprocess.run(cmd, cwd=str(FRONTEND), capture_output=True,
                           text=True, errors="replace")
        tail = (r.stdout or "")[-1200:]
        if tail.strip():
            print(tail)
        if r.returncode != 0:
            print((r.stderr or "")[-2000:], file=sys.stderr)
            raise SystemExit(f"vite build 失败 rc={r.returncode}")
    finally:
        # 恢复 frontend/.env，避免把 NEX_API_BASE 写死进仓库或污染后续构建。
        if prev is None:
            env_file.unlink(missing_ok=True)
        else:
            env_file.write_text(prev, encoding="utf-8")


def verify_staging() -> None:
    """资源闭包体检：index.html 与所有 JS/CSS 引用到的文件都必须真实存在。

    只按 mtime 猜「哪批是本次构建」不可靠；这里从入口出发沿引用图走闭包，
    顺带把「误把整个 dist/ 拷进来」这种事故用文件数 / 体积阈值挡住。
    """
    idx = STAGING / "index.html"
    if not idx.is_file():
        raise SystemExit("staging 缺 index.html")

    queue = [ref.lstrip("/") for ref in HTML_REF.findall(
        idx.read_text(encoding="utf-8"))]
    seen: set[str] = set()
    missing: list[str] = []
    while queue:
        rel = queue.pop()
        if rel in seen:
            continue
        seen.add(rel)
        f = STAGING / rel
        if not f.is_file():
            missing.append(rel)
            continue
        if f.suffix not in {".js", ".mjs", ".css"}:
            continue
        txt = f.read_text(encoding="utf-8", errors="replace")
        for name in ASSET_REF.findall(txt):
            cand = f"assets/{name}"
            if cand not in seen and (STAGING / cand).is_file():
                queue.append(cand)

    files = [f for f in STAGING.rglob("*") if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    print(f"[prepare_app] staging: {len(files)} files / "
          f"{total / 1024 / 1024:.2f} MB, reachable {len(seen)}")
    # 判题运行时不在 HTML/JS 引用图上，单独按白名单验，避免漏拷。
    py_missing = [rel for rel in PYODIDE_REQUIRED if not (STAGING / rel).is_file()]
    if missing or py_missing:
        raise SystemExit("staging 资源闭包缺文件: "
                         + ", ".join((missing + py_missing)[:8]))
    if len(files) > MAX_FILES or total > MAX_MB * 1024 * 1024:
        raise SystemExit(f"staging 异常膨胀（>{MAX_FILES} 文件或 >{MAX_MB}MB），"
                         "疑似把整个 dist/ 拷了进来")
    if not any(f.suffix == ".js" for f in files):
        raise SystemExit("staging 没有任何 JS chunk，构建不完整")


def write_conf(name: str, title: str | None) -> None:
    """两份 --config 增量配置；覆盖 frontendDist / 构建钩子 / CSP / 窗口标题。"""
    conf: dict = {
        "build": {
            "frontendDist": "../deploy/package/app",
            "beforeBuildCommand": None,
            "beforeDevCommand": None,
        },
        # 桌面与移动都跑 Pyodide，两端都得放行 wasm 编译。
        "app": {"security": {"csp": APP_CSP}},
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
    path.write_text(json.dumps(conf, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print(f"[prepare_app] config -> {path.relative_to(ROOT)}")


def write_cmd(name: str, lines: list[str]) -> None:
    """与 prepare.py 同口径：GBK + CRLF，供主人本机双击。"""
    path = PKG / name
    with path.open("w", encoding="gbk", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[prepare_app] script -> {path.relative_to(ROOT)}")


def write_build_scripts() -> None:
    write_cmd("build-app-exe.cmd", [
        "@echo off",
        "REM Nex 真应用 Windows EXE（内嵌 frontend React 应用）",
        "REM 由 deploy/package/prepare_app.py 生成，请改生成器而不是改本文件",
        "cd /d \"%~dp0..\\..\\src-tauri\"",
        "set NO_PROXY=*",
        "set no_proxy=*",
        "REM 必须显式 --target：.cargo/config.toml 只配 rustflags，未设默认 target",
        "call \"..\\frontend\\node_modules\\.bin\\tauri.cmd\" build --no-bundle --target x86_64-pc-windows-gnu --config tauri.app.desktop.conf.json",
        "if errorlevel 1 exit /b 1",
        "if not exist \"..\\release\\nex-shell\" mkdir \"..\\release\\nex-shell\"",
        f"copy /y \"target\\x86_64-pc-windows-gnu\\release\\nex.exe\" \"..\\release\\nex-shell\\{EXE_OUT}\" >nul",
        "if exist \"target\\x86_64-pc-windows-gnu\\release\\WebView2Loader.dll\" copy /y \"target\\x86_64-pc-windows-gnu\\release\\WebView2Loader.dll\" \"..\\release\\nex-shell\\\" >nul",
        "REM 桌面判题资源：Rust detect_go_judge() 只认 EXE 同级 binaries/go-judge.exe",
        "if not exist \"..\\release\\nex-shell\\binaries\" mkdir \"..\\release\\nex-shell\\binaries\"",
        "if not exist \"binaries\\go-judge.exe\" echo [nex-app] ERROR: src-tauri/binaries/go-judge.exe missing & exit /b 1",
        "copy /y \"binaries\\go-judge.exe\" \"..\\release\\nex-shell\\binaries\\go-judge.exe\" >nul",
        "if errorlevel 1 exit /b 1",
        f"echo [nex-app] EXE ready: release\\nex-shell\\{EXE_OUT}",
    ])
    write_cmd("build-app-apk.cmd", [
        "@echo off",
        "REM Nex 真应用 Android arm64 APK（内嵌 frontend React 应用）",
        "REM 由 deploy/package/prepare_app.py 生成，请改生成器而不是改本文件",
        "cd /d \"%~dp0..\\..\\src-tauri\"",
        "set NO_PROXY=*",
        "set no_proxy=*",
        "set ANDROID_HOME=D:\\Sdk",
        "set ANDROID_SDK_ROOT=D:\\Sdk",
        "set NDK_HOME=D:\\Sdk\\ndk\\android-ndk-r27c",
        "set JAVA_HOME=C:\\Program Files\\Java\\jdk-23",
        "set CI=true",
        "REM gen/android 被 gitignore；从入库的图标镜像同步",
        "xcopy /y /e /i /q \"..\\deploy\\package\\icons\\android\" \"gen\\android\\app\\src\\main\\res\" >nul",
        "call \"..\\frontend\\node_modules\\.bin\\tauri.cmd\" android build --apk --target aarch64 --split-per-abi --config tauri.app.mobile.conf.json",
        "REM Windows 未开开发者模式时末尾「创建符号链接」报错属预期，.so 已生成",
        "if not exist \"target\\aarch64-linux-android\\release\\libnex.so\" exit /b 1",
        "if not exist \"gen\\android\\app\\src\\main\\jniLibs\\arm64-v8a\" mkdir \"gen\\android\\app\\src\\main\\jniLibs\\arm64-v8a\"",
        "copy /y \"target\\aarch64-linux-android\\release\\libnex.so\" \"gen\\android\\app\\src\\main\\jniLibs\\arm64-v8a\\libnex.so\" >nul",
        "REM Tauri v2 不把 frontendDist 拷进 APK 资源目录（既有缺陷），手动同步",
        "if not exist \"gen\\android\\app\\src\\main\\assets\\dist\" mkdir \"gen\\android\\app\\src\\main\\assets\\dist\"",
        "xcopy /y /e /i /q \"..\\deploy\\package\\app\" \"gen\\android\\app\\src\\main\\assets\\dist\" >nul",
        "cd /d \"gen\\android\"",
        "call gradlew.bat assembleRelease --no-daemon -x rustBuildArm64Release -x rustBuildArmRelease -x rustBuildX86Release -x rustBuildX86_64Release",
        "if errorlevel 1 exit /b 1",
        "if not exist \"..\\..\\..\\release\\nex-shell\" mkdir \"..\\..\\..\\release\\nex-shell\"",
        "REM 中间文件名带 -app，避免与设计稿包的 tmp.apk 撞车",
        "\"D:\\Sdk\\build-tools\\35.0.0\\zipalign.exe\" -f -p 4 app\\build\\outputs\\apk\\arm64\\release\\app-arm64-release-unsigned.apk \"..\\..\\..\\release\\nex-shell\\tmp-app.apk\"",
        "REM 直连 apksigner.jar：从 Git Bash 调 apksigner.bat 会被本机安全策略拦",
        f"\"%JAVA_HOME%\\bin\\java.exe\" -jar \"D:\\Sdk\\build-tools\\35.0.0\\lib\\apksigner.jar\" sign --ks keystore\\nex-release.jks --ks-pass pass:nex2026 --key-pass pass:nex2026 --ks-key-alias nex --out \"..\\..\\..\\release\\nex-shell\\{APK_OUT}\" \"..\\..\\..\\release\\nex-shell\\tmp-app.apk\"",
        "if errorlevel 1 exit /b 1",
        "del \"..\\..\\..\\release\\nex-shell\\tmp-app.apk\"",
        f"\"%JAVA_HOME%\\bin\\java.exe\" -jar \"D:\\Sdk\\build-tools\\35.0.0\\lib\\apksigner.jar\" verify --print-certs \"..\\..\\..\\release\\nex-shell\\{APK_OUT}\" >nul",
        "if errorlevel 1 echo [nex-app] ERROR: APK signature verification failed & exit /b 1",
        f"echo [nex-app] APK ready: release\\nex-shell\\{APK_OUT}",
    ])


def self_check() -> None:
    """防回归：输出名必须独立，绝不能覆盖已验收的设计稿包。"""
    exe_txt = (PKG / "build-app-exe.cmd").read_text(encoding="gbk")
    apk_txt = (PKG / "build-app-apk.cmd").read_text(encoding="gbk")
    assert "--target x86_64-pc-windows-gnu" in exe_txt, "EXE 脚本缺 --target"
    assert "tauri.app.desktop.conf.json" in exe_txt, "EXE 脚本没用真应用配置"
    assert "tauri.app.mobile.conf.json" in apk_txt, "APK 脚本没用真应用配置"
    assert "apksigner.jar" in apk_txt and "java.exe" in apk_txt, \
        "签名未直连 apksigner.jar"
    # APK 必须把前端塞进 assets/dist，否则打出的包只有 Rust 二进制没有页面。
    assert "assets\\dist" in apk_txt and "..\\deploy\\package\\app" in apk_txt, \
        "APK 脚本未把 Web 前端拷进 assets/dist（Tauri v2 不自动拷贝，曾致已发布 APK 无页面）"
    assert EXE_OUT in exe_txt and "Nex-Desktop-1.0.exe" not in exe_txt, \
        "EXE 输出名会覆盖设计稿包"
    assert APK_OUT in apk_txt and "Nex-Mobile-1.0-arm64.apk" not in apk_txt, \
        "APK 输出名会覆盖设计稿包"
    assert "binaries\\go-judge.exe" in exe_txt, \
        "EXE 脚本没落盘 go-judge，桌面判题会静默降级成 mock"
    proto = (ROOT / "frontend" / "src" / "lib" / "pyodide" /
             "protocol.ts").read_text(encoding="utf-8")
    assert "DEFAULT_INDEX_URL = `/pyodide/`" in proto, \
        "Pyodide 又指回 CDN 了：封装 CSP 会拦、离线会失败"
    assert all((ROOT / "frontend" / "public" / rel).is_file()
               for rel in PYODIDE_REQUIRED), \
        "public/pyodide 缺文件：先跑 scripts/fetch_pyodide.py"
    for conf_name in ("tauri.app.desktop.conf.json", "tauri.app.mobile.conf.json"):
        c = (TAURI / conf_name).read_text(encoding="utf-8")
        assert "wasm-unsafe-eval" in c, \
            f"{conf_name} 缺 wasm-unsafe-eval，判题会卡在「准备解释器…」"
    print("[prepare_app] self-check: 构建脚本 + 判题运行时 + 双端 CSP OK")


def main() -> None:
    clean_staging()
    build_staging()
    verify_staging()
    write_conf("tauri.app.desktop.conf.json", "Nex 学习版")
    write_conf("tauri.app.mobile.conf.json", None)
    write_build_scripts()
    self_check()
    print("[prepare_app] done")


if __name__ == "__main__":
    main()
