"""真 Postgres 端到端验收：Nex 后端昵称校验 + 进度整份快照。

用 embedded-postgres（本地 PG 18.6 二进制）起一个临时库，验证：
  1. 迁移脚本 migrate_add_study_state_snapshot 在 PG 上能正确 ADD JSONB 列；
  2. /api/v1/users/me 昵称校验（控制字符/超长→400，空白折叠，空串清除）；
  3. /api/v1/progress/state 整份 ProgressState 快照 PUT/GET 往返一致；
  4. 非对象 snapshot → 400；
  5. legacy 5 字段回退（snapshot=null，扁平字段并集生效）。

运行：python scripts/verify_nex_parity_pg.py   （cwd=server）
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys

# 把 server 根目录加入 path，使 `app` 包可被导入（脚本位于 server/scripts/ 下）
SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_ROOT)

from sqlalchemy import text

# 数据库来源：优先用外部注入的 DATABASE_URL（CI 用 postgres service container），
# 否则回退到本地 embedded-postgres（Windows 机器，含 PG 18.6 二进制）起临时库。
# embedded_postgres 仅在本分支按需导入，CI 不装它也能跑。
EXTERNAL_DB = os.environ.get("DATABASE_URL")
server = None
if EXTERNAL_DB:
    APG = EXTERNAL_DB.replace("postgresql://", "postgresql+asyncpg://")
    os.environ["DATABASE_URL"] = APG
    print(f"[setup] 使用外部 DATABASE_URL: {APG}")
else:
    import embedded_postgres as ep

    PGDATA = os.environ.get("EMBEDDED_PG_PGDATA", "D:/WB_Workspace/_tmp_pg_verify/pgdata")
    server = ep.get_server(pgdata=PGDATA, cleanup_mode="stop")
    server.ensure_pgdata_inited()
    server.ensure_postgres_running()
    uri = server.get_uri()
    APG = uri.replace("postgresql://", "postgresql+asyncpg://")
    os.environ["DATABASE_URL"] = APG
    print(f"[setup] embedded PG at {APG}")

# 必须在 import app 之前设置 DATABASE_URL，让 config 读到 PG
from app.db import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401 注册模型
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.models.user import User, UserProfile  # noqa: E402
from app.main import app  # noqa: E402


async def setup_db() -> None:
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        for uid in range(1, 5):
            s.add(User(id=uid, email=f"u{uid}@pg.dev", password_hash=hash_password("x")))
            s.add(UserProfile(user_id=uid, nickname=f"u{uid}"))
        await s.commit()
    print("[setup] 建表 + 测试用户就绪")


async def check_migration() -> None:
    # 先建好的表已含 snapshot 列，DROP 后再跑迁移，验证 ADD 路径
    async with engine.begin() as c:
        await c.execute(text("ALTER TABLE study_state DROP COLUMN IF EXISTS snapshot"))
    r = subprocess.run(
        [sys.executable, "-m", "scripts.migrate_add_study_state_snapshot"],
        env={**os.environ},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr[-800:]
    async with engine.connect() as c:
        udt = (
            await c.execute(
                text(
                    "SELECT udt_name FROM information_schema.columns "
                    "WHERE table_name='study_state' AND column_name='snapshot'"
                )
            )
        ).scalar()
        assert udt == "jsonb", f"期望 jsonb，实际 {udt}"
    print("[OK] 迁移 ADD snapshot 成功，类型=jsonb")


async def test_nickname(client, token: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    r = await client.patch("/api/v1/users/me", json={"nickname": "a\x07b"}, headers=h)
    assert r.status_code == 400, r.text
    r = await client.patch("/api/v1/users/me", json={"nickname": "x" * 25}, headers=h)
    assert r.status_code == 400, r.text
    # 空白折叠：PATCH 不回显，用 GET /users/me 验证已落库
    r = await client.patch(
        "/api/v1/users/me", json={"nickname": "  hello  world  "}, headers=h
    )
    assert r.status_code == 200, r.text
    g = await client.get("/api/v1/users/me", headers=h)
    assert g.json()["data"]["profile"]["nickname"] == "hello world", g.text
    # 空串 = 清除
    r = await client.patch("/api/v1/users/me", json={"nickname": ""}, headers=h)
    assert r.status_code == 200, r.text
    g = await client.get("/api/v1/users/me", headers=h)
    assert g.json()["data"]["profile"]["nickname"] == "", g.text
    print("[OK] 昵称校验：控制字符/超长→400，空白折叠，空串清除")


async def test_snapshot(client, token: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    snap = {
        "doneChapters": ["cpp-ch01", "cpp-ch02"],
        "doneProjects": ["p1"],
        "checkins": ["2026-01-01"],
        "coins": 1500,
        "outfit": "rogue",
        "theme": "dark",
        "answers": {"cpp-ch01-01": {"ok": True, "at": "2026-01-01T00:00:00"}},
        "chapterRuns": {},
        "bestiary": {},
        "weekly": None,
        "daily": [],
        "shards": 3,
    }
    r = await client.put(
        "/api/v1/progress/state", json={"snapshot": snap, "client_rev": 7}, headers=h
    )
    assert r.status_code == 200, r.text
    g = await client.get("/api/v1/progress/state", headers=h)
    d = g.json()["data"]
    assert d["snapshot"]["doneChapters"] == ["cpp-ch01", "cpp-ch02"], d["snapshot"]
    assert d["snapshot"]["answers"]["cpp-ch01-01"]["ok"] is True, d["snapshot"]
    assert d["client_rev"] == 7, d
    print("[OK] 进度整份快照 PUT/GET 往返一致")


async def test_nonobject(client, token: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    r = await client.put(
        "/api/v1/progress/state",
        json={"snapshot": "not-a-dict", "client_rev": 1},
        headers=h,
    )
    assert r.status_code == 400, r.text
    print("[OK] 非对象 snapshot → 400")


async def test_legacy(client, token: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    r = await client.put(
        "/api/v1/progress/state",
        json={
            "done_chapters": ["legacy-c1"],
            "done_projects": [],
            "checkins": ["2026-02-02"],
            "coins": 9,
            "outfit": "default",
            "theme": "light",
            "client_rev": 2,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    g = await client.get("/api/v1/progress/state", headers=h)
    d = g.json()["data"]
    assert d["snapshot"] is None, d
    assert "legacy-c1" in d["done_chapters"], d
    print("[OK] legacy 5 字段回退：snapshot=null，扁平字段并集生效")


async def main() -> None:
    await setup_db()
    await check_migration()
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await test_nickname(client, create_access_token(1))
        await test_snapshot(client, create_access_token(2))
        await test_nonobject(client, create_access_token(4))
        await test_legacy(client, create_access_token(3))
    print("\nPG_PARITY_OK  — Nex 后端在真 Postgres 上端到端通过")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if server is not None:
            try:
                server.cleanup()
            except Exception:
                pass
