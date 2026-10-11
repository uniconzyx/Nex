#!/usr/bin/env python3
"""Nex 桌面一键启动器（纯标准库，PyInstaller 打包为 Nex-Launcher.exe）。

职责：检测 Docker -> `docker compose up -d` 起全部服务 -> 等待 /health ->
自动打开 web-preview/index.html 演示页。不做后端逻辑，便于安全分发。

用法：
    Nex-Launcher.exe            # 完整流程
    Nex-Launcher.exe --dry-run  # 仅打印将执行的操作，不真正运行
    Nex-Launcher.exe --version  # 打印版本
    Nex-Launcher.exe --no-browser  # 起服务但不打开浏览器

依赖：本机需安装 Docker Desktop（https://www.docker.com/products/docker-desktop/）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

VERSION = "1.0.0"
HEALTH_URLS = ["http://localhost:8000/health", "http://localhost/health"]
HEALTH_TIMEOUT_S = 180


def log(msg: str) -> None:
    print(f"[Nex-Launcher] {msg}", flush=True)


def find_project_root() -> Path:
    """从可执行文件/脚本位置向上查找含 content/cpp/_manifest.json 的目录。"""
    here = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
    candidates = [here, *here.parents]
    for p in candidates:
        if (p / "content" / "cpp" / "_manifest.json").is_file():
            return p
    # 回退：假设 exe 位于 deploy/launcher/
    fallback = here.parents[2] if len(here.parents) >= 3 else here
    log(f"未在上溯路径中找到项目根，回退到 {fallback}")
    return fallback


def docker_compose_bin() -> tuple[list[str], str]:
    """返回 (compose 调用前缀, 可读名称)。优先 docker compose(v2)，其次 docker-compose。"""
    if shutil.which("docker"):
        # 探测 v2 插件
        r = subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if r.returncode == 0:
            return ["docker", "compose"], "docker compose (v2)"
        return ["docker-compose"], "docker-compose (v1)"
    return [], ""


def wait_health() -> str | None:
    deadline = time.time() + HEALTH_TIMEOUT_S
    while time.time() < deadline:
        for url in HEALTH_URLS:
            try:
                with urlopen(url, timeout=2) as resp:
                    if resp.status == 200:
                        log(f"服务已就绪：{url}")
                        return url
            except Exception:  # noqa: BLE001
                pass
        time.sleep(2)
    return None


def stream_compose(cmd: list[str], cwd: Path) -> int:
    """实时转发 docker compose 输出。"""
    proc = subprocess.Popen(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(f"  {line.rstrip()}", flush=True)
    return proc.wait()


def main() -> int:
    ap = argparse.ArgumentParser(description="Nex 桌面一键启动器")
    ap.add_argument("--version", action="store_true", help="打印版本并退出")
    ap.add_argument("--dry-run", action="store_true", help="仅打印操作，不真正执行")
    ap.add_argument("--no-browser", action="store_true", help="起服务但不打开浏览器")
    args = ap.parse_args()

    if args.version:
        print(f"Nex-Launcher {VERSION}")
        return 0

    root = find_project_root()
    compose_file = root / "deploy" / "docker-compose.yml"
    preview = root / "web-preview" / "index.html"

    log(f"项目根: {root}")
    log(f"compose: {compose_file}")
    log(f"演示页: {preview}")

    if args.dry_run:
        log("[dry-run] 将执行：检测 Docker -> docker compose up -d -> 等待 /health -> 打开浏览器")
        log(f"[dry-run] health 探测: {HEALTH_URLS}")
        log(f"[dry-run] 浏览器目标: {preview if preview.exists() else '<web-preview/index.html 不存在>'}")
        return 0

    if not compose_file.is_file():
        log(f"未找到 {compose_file}，无法启动。请确认仓库结构完整。")
        return 2

    compose, name = docker_compose_bin()
    if not compose:
        log("未检测到 Docker。请先安装 Docker Desktop：https://www.docker.com/products/docker-desktop/")
        if preview.exists() and not args.no_browser:
            log("（无后端时仍可打开产品演示页，但对话/测验等需后端的功能不可用）")
            webbrowser.open(preview.as_uri())
        input("按回车退出...")
        return 3

    log(f"检测到 {name}，正在启动服务（首次构建镜像可能较慢）...")
    up = ["up", "-d"] + ([] if args.dry_run else [])
    rc = stream_compose(compose + up + ["-f", str(compose_file)], root / "deploy")
    if rc != 0:
        log(f"docker compose up 返回非零退出码 {rc}，请检查 Docker Desktop 是否正常运行。")
        input("按回车退出...")
        return rc

    log(f"服务启动中，最长等待 {HEALTH_TIMEOUT_S}s 健康检查...")
    health = wait_health()
    if health is None:
        log("等待 /health 超时。服务可能仍在启动，或依赖（Postgres/Redis）未就绪。")
        log("可稍后手动访问：http://localhost:8000/docs")
    else:
        log(f"后端健康：{health}")

    if not args.no_browser and preview.exists():
        log(f"打开演示页：{preview}")
        webbrowser.open(preview.as_uri())
    elif not args.no_browser:
        log("未找到 web-preview/index.html，请手动访问 http://localhost:8000/docs")

    if health is None:
        input("按回车退出...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
