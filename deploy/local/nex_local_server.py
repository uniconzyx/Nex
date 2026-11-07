#!/usr/bin/env python3
"""Nex 本机部署服务：同源托管 UI + 契约一致的持久化 API（SQLite）。

为什么是这一层，而不是直接 uvicorn app.main:app：
  server/app 是完整微服务后端，默认连 PostgreSQL；本机 5432 无服务，
  Docker 被主机安全策略限制无法由程序拉起，embedded_postgres 在「进程被
  强杀 -> PG 崩溃恢复 -> pg_ctl 内置 10s 超时」这条链路上会反复起不来。
  本机部署追求的是「双击就能用、重启数据还在」，所以这里内嵌一个轻量 API，
  接口契约与 server/app 的 /api/v1/progress/state 完全一致（统一响应包、
  Bearer、整份快照 GET/PUT），数据落 SQLite；不引入任何守护进程。

需要完整后端（题库 / 判题 / Redis / 全量用户体系）时：
  用 Docker Compose 或外部 PG 起 server/app，然后在页面里执行
    localStorage.setItem('nex.apiBaseUrl', 'http://<host>:8000')
  共享层会改连真后端；本服务无需改动，页面与数据协议是同一套。

同源托管的意义：
  web-preview/ 是 APK 竖屏版 / EXE 桌面版（与 Tauri 打包的 dist/ 是两套 UI）。
  挂到同一个进程的 /app 下后，API 与页面同源：不依赖 CORS、不依赖
  file:// 的 null origin 白名单，手机/平板走局域网 IP 也能连到同一后端。

启动：  python deploy/local/nex_local_server.py
端口：  默认 8000（NEX_PORT 可覆盖），绑定 0.0.0.0 供局域网访问
数据：  NEX_LOCAL_DATA 指定目录（默认 D:/WB_Workspace/_nex_local），
        内含 state.db、server.log、server.pid
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import threading
import time
import uuid

from fastapi import Body, FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

ROOT = pathlib.Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web-preview"
DATA_DIR = pathlib.Path(os.environ.get("NEX_LOCAL_DATA", "D:/WB_Workspace/_nex_local"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "state.db"

LOCAL_TOKEN = "nex-local-device"          # 本机设备令牌，不需要反复登录
MAX_SNAPSHOT_BYTES = 1024 * 1024          # 与 server/app 的 MAX_SNAPSHOT_BYTES 对齐
_db_lock = threading.Lock()


def envelope(data, message: str = "ok", code: int = 0) -> dict:
    """与 server/app/core/responses.py 的统一响应包一致。"""
    return {"code": code, "message": message, "data": data, "traceId": uuid.uuid4().hex[:12]}


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS study_state (
               user_id INTEGER PRIMARY KEY,
               snapshot TEXT,
               updated_at TEXT NOT NULL
           )"""
    )
    conn.commit()
    return conn


def read_snapshot() -> dict | None:
    # sqlite3 的 connection 上下文只提交事务、不关闭连接，必须显式 close
    with _db_lock:
        conn = connect_db()
        try:
            row = conn.execute("SELECT snapshot FROM study_state WHERE user_id = 1").fetchone()
        finally:
            conn.close()
    if not row or not row[0]:
        return None
    try:
        return json.loads(row[0])
    except (ValueError, TypeError):
        return None


def write_snapshot(snap: dict) -> None:
    raw = json.dumps(snap, ensure_ascii=False)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _db_lock:
        conn = connect_db()
        try:
            conn.execute(
                """INSERT INTO study_state (user_id, snapshot, updated_at) VALUES (1, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET snapshot = excluded.snapshot,
                                                     updated_at = excluded.updated_at""",
                (raw, now),
            )
            conn.commit()
        finally:
            conn.close()


def require_auth(authorization: str | None) -> JSONResponse | None:
    """契约与 get_current_user 一致：缺 Bearer 返回 401 统一响应包。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return JSONResponse(
            status_code=401,
            content=envelope(None, "未登录", code=40101),
        )
    return None


app = FastAPI(title="Nex Local", version="1.0.0", docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return envelope({"status": "up"})


@app.get("/api/local/session")
async def local_session():
    """共享层在无令牌时自动领取；之后所有请求都带 Bearer。"""
    return envelope({"access_token": LOCAL_TOKEN, "user_id": 1, "mode": "local"})


@app.get("/api/local/status")
async def local_status():
    """部署自检：看数据是否真的落盘。"""
    with _db_lock:
        conn = connect_db()
        try:
            row = conn.execute(
                "SELECT updated_at, length(snapshot) FROM study_state WHERE user_id = 1"
            ).fetchone()
        finally:
            conn.close()
    return envelope({
        "db": str(DB_PATH),
        "has_snapshot": bool(row and row[1]),
        "snapshot_bytes": row[1] if row else 0,
        "updated_at": row[0] if row else None,
    })


@app.get("/api/v1/progress/state")
async def get_state(authorization: str | None = Header(default=None)):
    denied = require_auth(authorization)
    if denied:
        return denied
    snap = read_snapshot()
    # 无快照时返回 null：共享层 applyRemote 会保留本地状态，不会把进度清空
    return envelope({"snapshot": snap})


@app.put("/api/v1/progress/state")
async def put_state(
    body: dict = Body(...),
    authorization: str | None = Header(default=None),
):
    denied = require_auth(authorization)
    if denied:
        return denied
    snap = body.get("snapshot")
    if not isinstance(snap, dict):
        return JSONResponse(
            status_code=400,
            content=envelope(None, "snapshot 必须是对象", code=40001),
        )
    if len(json.dumps(snap, ensure_ascii=False).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        return JSONResponse(
            status_code=400,
            content=envelope(None, "进度快照过大（>1MB）", code=40001),
        )
    write_snapshot(snap)
    return envelope({"ok": True, "bytes": len(json.dumps(snap, ensure_ascii=False).encode("utf-8"))})


@app.get("/", include_in_schema=False)
async def root():
    # 本机默认打开桌面版；竖屏版 /app/kaimao-mobile.html 单独给快捷方式
    return RedirectResponse("/app/kaimao-desktop.html")


# 挂在最后，避免抢占 /health、/api/v1、/api/local/session
app.mount("/app", StaticFiles(directory=str(WEB_DIR), html=True), name="nex-app")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("NEX_PORT", "8000"))
    print(f"[nex-local] db={DB_PATH}", flush=True)
    print(f"[nex-local] serving {WEB_DIR} at http://0.0.0.0:{port}/", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
