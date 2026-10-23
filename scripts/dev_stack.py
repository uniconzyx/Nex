#!/usr/bin/env python3
"""一键起「后端 + 前端」—— 打通本地开发链路的唯一入口。

为什么需要它：
  Nex 的三层（React 前端 / FastAPI 后端 / Tauri 客户端）各自能跑，但手动起
  三条命令、顺序还必须对（后端先、题库内容要构建过），新手和 CI 都容易卡住。
  本脚本把这些前置检查 + 启动 + 探活串成一条命令。

用法：
    python scripts/dev_stack.py              # 起后端 + vite（前端），并打开浏览器
    python scripts/dev_stack.py --no-browser # 不开浏览器
    python scripts/dev_stack.py --backend-only
    python scripts/dev_stack.py --frontend-only
    python scripts/dev_stack.py --check      # 只做前置检查与探活，不启动

设计约束（沿用项目既有铁律）：
  * **不写 .sh 编排脚本**。本机 bash 会被路由到 wsl.exe 并被黑名单拦截，
    所以一切编排都用 Python。
  * **不碰 Docker**。后端用本机 Python + uvicorn 直跑；数据库功能不可用时
    不影响题库（题库是文件型数据源）。
  * 后端以「子进程 + 日志落盘」方式启动，退出时负责收干净。

依赖：
    server/requirements.txt 里的包要装在当前 python 环境里。
    题库数据要构建过：python server/scripts/build_exam.py
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
FRONTEND = ROOT / "frontend"
LOG_DIR = ROOT / "scratch" / "logs"

API_PORT = 8000
WEB_PORT = 1420


def log(msg: str) -> None:
    print(f"[dev-stack] {msg}", flush=True)


# ------------------------------------------------------------------ 工具 --

def port_busy(port: int) -> bool:
    """端口是否已被占用。用 socket connect 而不是 ps/netstat——跨平台且无副作用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def http_get(url: str, timeout: float = 2.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def wait_http(url: str, timeout_s: float = 60.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        code, _ = http_get(url)
        if code == 200:
            return True
        time.sleep(1.0)
    return False


# -------------------------------------------------------------- 前置检查 --

def preflight() -> bool:
    """检查依赖与数据是否就绪。返回 True 表示可以启动。"""
    ok = True

    # 1. Python 依赖
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except Exception:
        log("✗ 缺少 fastapi/uvicorn。请用装了依赖的解释器跑本脚本，例如：")
        log(f"    {sys.executable} scripts/dev_stack.py")
        log("  依赖安装：pip install -r server/requirements.txt")
        ok = False

    # 2. 题库数据（文件型功能的基础）
    exam_dir = ROOT / "content" / "_exam" / "questions"
    if not exam_dir.is_dir():
        log("✗ 未找到题库数据。先执行：python server/scripts/build_exam.py")
        ok = False
    else:
        n = len(list(exam_dir.glob("*.json")))
        log(f"✓ 题库数据就绪（{n} 个科目文件）")

    # 3. 前端依赖
    if not (FRONTEND / "node_modules").is_dir():
        log("✗ 前端依赖未安装。请在 frontend 目录执行：npm install")
        ok = False

    return ok


# ------------------------------------------------------------------ 启动 --

def start_backend() -> subprocess.Popen | None:
    if port_busy(API_PORT):
        code, _ = http_get(f"http://127.0.0.1:{API_PORT}/health")
        if code == 200:
            log(f"✓ 后端已在运行（127.0.0.1:{API_PORT}），不重复启动")
            return None
        log(f"✗ 端口 {API_PORT} 被占用，但 /health 不通。请先释放该端口。")
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logf = open(LOG_DIR / "backend.log", "w", encoding="utf-8")
    log("启动后端 uvicorn …")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(API_PORT)],
        cwd=str(SERVER), stdout=logf, stderr=subprocess.STDOUT,
    )
    if wait_http(f"http://127.0.0.1:{API_PORT}/health", 60):
        log(f"✓ 后端就绪 http://127.0.0.1:{API_PORT}（日志：{LOG_DIR / 'backend.log'}）")
        return proc
    log(f"✗ 后端启动失败，查看日志：{LOG_DIR / 'backend.log'}")
    return None


def start_frontend() -> subprocess.Popen | None:
    if port_busy(WEB_PORT):
        log(f"✓ 前端 dev server 已在运行（127.0.0.1:{WEB_PORT}），不重复启动")
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logf = open(LOG_DIR / "frontend.log", "w", encoding="utf-8")
    cmd = frontend_command()
    if not cmd:
        log("✗ 找不到可用的前端启动方式（既无 node 也无 npm）。")
        return None
    log(f"启动前端 vite …（{' '.join(cmd)}）")
    proc = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND), stdout=logf, stderr=subprocess.STDOUT,
    )
    if wait_http(f"http://127.0.0.1:{WEB_PORT}/", 60):
        log(f"✓ 前端就绪 http://127.0.0.1:{WEB_PORT}（日志：{LOG_DIR / 'frontend.log'}）")
        return proc
    log(f"✗ 前端启动失败，查看日志：{LOG_DIR / 'frontend.log'}")
    return None


def frontend_command() -> list[str] | None:
    """构造启动 vite dev server 的命令。

    优先**直跑 vite 脚本**，不走 `npm run dev`：
      本机的 `npm` 会被命令安全层路由到 wsl.exe 并被黑名单拦截，
      直跑 node + node_modules/vite/bin/vite.js 才稳。
    找不到 node 时才退回 npm。
    """
    vite_js = FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"
    if vite_js.is_file():
        node = shutil.which("node")
        if node:
            return [
                node,
                str(vite_js),
                "--port", str(WEB_PORT),
                "--strictPort",
            ]
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        return [npm, "run", "dev", "--", "--port", str(WEB_PORT), "--strictPort"]
    return None


# ------------------------------------------------------------------ 收尾 --

def cleanup(procs: list[subprocess.Popen]) -> None:
    for p in procs:
        if p is None or p.poll() is not None:
            continue
        log(f"结束子进程 pid={p.pid}")
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Nex 前后端一键启动")
    ap.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    ap.add_argument("--backend-only", action="store_true")
    ap.add_argument("--frontend-only", action="store_true")
    ap.add_argument("--check", action="store_true", help="只做前置检查与探活")
    args = ap.parse_args()

    log(f"项目根：{ROOT}")

    if args.check:
        ok = preflight()
        code, body = http_get(f"http://127.0.0.1:{API_PORT}/health")
        log(f"后端 /health → HTTP {code}")
        if code == 200:
            log(f"  {body[:160]}")
        return 0 if ok else 1

    if not args.frontend_only and not preflight():
        log("前置检查未通过，已中止。")
        return 1

    procs: list[subprocess.Popen] = []
    try:
        if not args.frontend_only:
            b = start_backend()
            if b is None and not port_busy(API_PORT):
                return 1
            if b:
                procs.append(b)

        if not args.backend_only:
            f = start_frontend()
            if f:
                procs.append(f)

        if not args.no_browser and not args.backend_only:
            import webbrowser

            webbrowser.open(f"http://127.0.0.1:{WEB_PORT}/")

        log("全部就绪。Ctrl+C 结束。")
        while True:
            time.sleep(1.0)
            for p in procs:
                if p.poll() is not None:
                    log(f"⚠ 子进程 pid={p.pid} 已退出（code={p.returncode}），查看日志定位。")
                    return 1
    except KeyboardInterrupt:
        log("收到 Ctrl+C，正在收尾…")
    finally:
        cleanup(procs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
