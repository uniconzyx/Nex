#!/usr/bin/env python3
"""Nex 本机服务守护：脱离终端常驻、健康检查、一键启停与打开独立窗口。

用法：
    python daemon.py start            # 后台常驻启动（detached，关掉终端也不停）
    python daemon.py stop             # 停止服务与它拉起的 PG
    python daemon.py status           # 查看状态与访问地址
    python daemon.py urls             # 只打印访问地址
    python daemon.py open desktop     # 用 Edge --app 打开桌面版独立窗口
    python daemon.py open mobile      # 用 Edge --app 打开竖屏版独立窗口
"""
from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = pathlib.Path(os.environ.get("NEX_LOCAL_DATA", "D:/WB_Workspace/_nex_local"))
DATA.mkdir(parents=True, exist_ok=True)

PY = ROOT / "server" / ".venv" / "Scripts" / "python.exe"
PYW = ROOT / "server" / ".venv" / "Scripts" / "pythonw.exe"
SERVER = ROOT / "deploy" / "local" / "nex_local_server.py"
PID_FILE = DATA / "server.pid"
LOG_FILE = DATA / "server.log"
PORT = int(os.environ.get("NEX_PORT", "8000"))

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
DETACH_FLAGS = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

EDGE_CANDIDATES = [
    pathlib.Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    pathlib.Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
]


def health(timeout: float = 1.0) -> bool:
    # 本机探测必须绕开系统代理：PAC/全局代理会把 127.0.0.1 请求转发到上游，
    # 返回 502「upstream connect failed」，造成服务明明在跑却误判为离线。
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{PORT}/health", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def lan_ip() -> str:
    """取真正能出外网的本机地址（避开 VMware / WSL 虚拟网卡）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("223.5.5.5", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def urls() -> None:
    ip = lan_ip()
    print(f"  Desktop : http://127.0.0.1:{PORT}/app/kaimao-desktop.html")
    print(f"  Mobile  : http://127.0.0.1:{PORT}/app/kaimao-mobile.html")
    print(f"  LAN(PC) : http://{ip}:{PORT}/app/kaimao-desktop.html")
    print(f"  LAN(手机): http://{ip}:{PORT}/app/kaimao-mobile.html")
    print(f"  API     : http://127.0.0.1:{PORT}/health")


def start() -> int:
    if health():
        print("[Nex] already running.")
        urls()
        return 0
    log = open(LOG_FILE, "ab", buffering=0)
    proc = subprocess.Popen(
        [str(PYW), str(SERVER)],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=DETACH_FLAGS,
        close_fds=True,
    )
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    print(f"[Nex] starting pid={proc.pid}, waiting for /health ...", flush=True)
    for _ in range(120):
        if health(1.0):
            print("[Nex] ready.")
            urls()
            return 0
        if proc.poll() is not None:
            break
        time.sleep(1)
    print(f"[Nex] start failed (or timed out). See log: {LOG_FILE}")
    try:
        print(LOG_FILE.read_text(encoding="utf-8", errors="replace")[-1500:])
    except Exception:
        pass
    return 1


def stop() -> int:
    if not PID_FILE.exists():
        print("[Nex] no pid file; nothing to stop.")
        return 0
    pid = PID_FILE.read_text(encoding="utf-8").strip()
    r = subprocess.run(
        ["taskkill", "/PID", pid, "/T", "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PID_FILE.unlink(missing_ok=True)
    print("[Nex] stopped." if r.returncode == 0 else f"[Nex] taskkill rc={r.returncode}")
    return 0 if r.returncode == 0 else 1


def status() -> int:
    running = health()
    pid = PID_FILE.read_text(encoding="utf-8").strip() if PID_FILE.exists() else "-"
    print(f"[Nex] running={running} pid={pid} port={PORT}")
    if running:
        urls()
    print(f"[Nex] log={LOG_FILE}")
    return 0 if running else 1


def open_window(mode: str = "desktop") -> int:
    if not health():
        print("[Nex] service is not running; run 'start' first.")
        return 1
    edge = next((p for p in EDGE_CANDIDATES if p.exists()), None)
    if edge is None:
        print("[Nex] Edge not found; open the URL in a browser:")
        urls()
        return 1
    page = "kaimao-mobile.html" if mode == "mobile" else "kaimao-desktop.html"
    size = "--window-size=430,932" if mode == "mobile" else "--window-size=1280,860"
    url = f"http://127.0.0.1:{PORT}/app/{page}"
    subprocess.Popen(
        [str(edge), f"--app={url}", size, "--no-first-run", "--no-default-browser-check"],
        creationflags=DETACH_FLAGS,
        close_fds=True,
    )
    print(f"[Nex] opened {mode} window: {url}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "start":
        return start()
    if cmd == "stop":
        return stop()
    if cmd == "status":
        return status()
    if cmd == "urls":
        urls()
        return 0
    if cmd == "open":
        return open_window(sys.argv[2] if len(sys.argv) > 2 else "desktop")
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
