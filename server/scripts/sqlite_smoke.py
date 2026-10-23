"""SQLite 冒烟：验证 app 能否在无 PostgreSQL 环境下启动 + 核心接口是否连通。

用法（工作目录 server/）：
    DATABASE_URL="sqlite+aiosqlite:///./.smoke.db" \
      python -m scripts.sqlite_smoke

设计取舍：
* 生产库是 PostgreSQL（JSONB / UUID 等方言类型），本脚本只做**冒烟**，
  不替代真库集成测试；目的是把"后端到底能不能跑、接口通不通"变成可复现证据。
* 用 `create_all` 建表，不走 alembic（离线环境拉不到 pg 驱动，迁移脚本无从校验）。
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./.smoke.db")

from httpx import ASGITransport, AsyncClient  # noqa: E402

FAIL: list[str] = []
PASS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")


async def main() -> int:
    from app.db import Base, engine
    from app.main import app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 1) 健康检查
        r = await c.get("/health")
        check("GET /health", r.status_code == 200 and r.json().get("data", {}).get("status") == "up",
              f"{r.status_code}")

        # 2) 注册
        email = "smoke@nex.dev"
        r = await c.post("/api/v1/auth/register", json={"email": email, "password": "Passw0rd!", "nickname": "冒烟"})
        body = r.json()
        check("POST /auth/register", r.status_code == 200 and body.get("code") == 0, f"{r.status_code} {body.get('message')}")

        # 3) 重复注册应被拒
        r = await c.post("/api/v1/auth/register", json={"email": email, "password": "Passw0rd!"})
        check("重复注册被拒", r.json().get("code") not in (0, None), str(r.json().get("message"))[:40])

        # 4) 登录
        r = await c.post("/api/v1/auth/login", json={"account": email, "password": "Passw0rd!"})
        data = r.json().get("data") or {}
        token = data.get("access_token")
        check("POST /auth/login", bool(token), f"token={bool(token)}")
        # 密码错
        r = await c.post("/api/v1/auth/login", json={"account": email, "password": "wrongpass"})
        check("错误密码拒绝", r.status_code == 401, str(r.status_code))

        h = {"Authorization": f"Bearer {token}"}

        # 5) 未登录访问私有接口
        r = await c.get("/api/v1/users/me")
        check("未登录 /users/me 401", r.status_code == 401, str(r.status_code))

        # 6) 已登录 /users/me
        r = await c.get("/api/v1/users/me", headers=h)
        me = r.json().get("data") or {}
        check("GET /users/me", me.get("email") == email, str(me.get("email")))

        # 7) 改昵称
        r = await c.patch("/api/v1/users/me", headers=h, json={"nickname": "改名成功"})
        r = await c.get("/api/v1/users/me", headers=h)
        nick = ((r.json().get("data") or {}).get("profile") or {}).get("nickname")
        check("PATCH /users/me 生效", nick == "改名成功", str(nick))

        # 8) refresh
        rt = data.get("refresh_token")
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        check("POST /auth/refresh", bool((r.json().get("data") or {}).get("access_token")))

        # 9) 公开接口（空库也应返回 200 + 空列表，不是 500）
        for path in ["/api/v1/courses", "/api/v1/guides", "/api/v1/career-tracks"]:
            r = await c.get(path)
            check(f"GET {path}", r.status_code == 200, f"{r.status_code}")

        # 10) 私有接口 + 登录态
        for path in ["/api/v1/progress/dashboard", "/api/v1/achievements/my", "/api/v1/ai/quota"]:
            r = await c.get(path, headers=h)
            check(f"GET {path} (auth)", r.status_code == 200, f"{r.status_code} {str(r.json())[:60]}")

        # 11) OpenAPI 路由清单
        r = await c.get("/openapi.json")
        paths = list((r.json().get("paths") or {}).keys())
        check("OpenAPI 路由 ≥ 40", len(paths) >= 40, f"{len(paths)} paths")

    report = {"pass": len(PASS), "fail": len(FAIL), "failed": FAIL,
              "out": str(Path("..").resolve() / ".scratch" / "backend-smoke.json")}
    Path(report["out"]).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n合计 {len(PASS)} PASS / {len(FAIL)} FAIL")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
