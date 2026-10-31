"""Nex 后端 ↔ 本地账号服务（auth-server）能力对齐验收。

覆盖 2026-10-31 的两处对齐：
  1. 昵称校验：与 auth-server 同规则（空白折叠单空格、≤24、拒控制字符、空串=清除）；
  2. 进度：/api/v1/progress/state 现支持整份 ProgressState 快照（含 answers /
     bestiary / chapterRuns / weekly），不再只是 5 个扁平字段；并验证迁移脚本
     能为既有库添加 study_state.snapshot 列。

用 SQLite 跑（离线可验证，无需 Docker / Postgres）。BigInt 自增在 SQLite 上不生效，
故插入用户时显式指定 id=1。
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./.parity_test.db")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text

from app.core.security import create_access_token, hash_password
from app.db import Base, SessionLocal, engine
from app.models.progress import Checkin, StudyState
from datetime import date
import app.models  # noqa: F401  注册全部模型
from app.main import app

TEST_EMAIL = "parity@nex.dev"
TEST_PW = "Passw0rd!"
UF_UUID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(scope="module")
async def client():
    # 干净库：删掉旧文件再建表（create_all 已含新的 snapshot 列）
    if os.path.exists(".parity_test.db"):
        os.remove(".parity_test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await db.execute(
            text(
                "INSERT OR IGNORE INTO users "
                "(id, email, phone, password_hash, role, status, last_login_at, uuid) "
                "VALUES (1, :email, NULL, :pw, 'user', 'active', NULL, :uuid)"
            ),
            {"email": TEST_EMAIL, "pw": hash_password(TEST_PW), "uuid": UF_UUID},
        )
        await db.execute(
            text(
                "INSERT OR IGNORE INTO user_profiles "
                "(user_id, nickname, avatar_url, daily_minutes, plan, theme, reduced_motion, font_scale) "
                "VALUES (1, '', '', 60, 'free', 'system', 0, 1.0)"
            )
        )
        # 预置 study_state 行（显式 id）。SQLite 上 BigInteger 主键不自增，
        # 若不预置，路由首次写入会触发 NOT NULL 失败——这是 SQLite 测试环境
        # 的既有限制（users 表同样如此），与本次改动无关；生产 Postgres 正常。
        # 预置后进度路由走 UPDATE 路径，可完整验证整份快照的存取/投影/校验。
        db.add(StudyState(id=1, user_id=1))
        # 预置测试用到的打卡日期（显式 id），让路由的「并集」逻辑发现已存在而
        # 跳过 INSERT，避免 sqlite 的 BigInteger 自增限制干扰快照往返验证。
        db.add(Checkin(id=1, user_id=1, day=date(2026, 10, 30)))
        db.add(Checkin(id=2, user_id=1, day=date(2026, 10, 31)))
        db.add(Checkin(id=3, user_id=1, day=date(2026, 1, 1)))
        await db.flush()
        await db.commit()

    token = create_access_token(1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


# ───────────────────────── 昵称校验 ─────────────────────────


async def test_nickname_rejects_control_char(client):
    r = await client.patch("/api/v1/users/me", json={"nickname": "喵\x07名"})
    assert r.status_code == 400, r.text


async def test_nickname_rejects_too_long(client):
    r = await client.patch("/api/v1/users/me", json={"nickname": "喵" * 25})
    assert r.status_code == 400, r.text


async def test_nickname_collapses_whitespace(client):
    # 连续空白（含换行）折叠成单空格并两端 trim
    r = await client.patch("/api/v1/users/me", json={"nickname": "  a\n\tb  "})
    assert r.status_code == 200, r.text
    me = (await client.get("/api/v1/users/me")).json()["data"]
    assert me["profile"]["nickname"] == "a b"


async def test_nickname_empty_clears(client):
    # 空串语义 = 清除自定义昵称（回退到用户名显示）
    r = await client.patch("/api/v1/users/me", json={"nickname": ""})
    assert r.status_code == 200, r.text
    me = (await client.get("/api/v1/users/me")).json()["data"]
    assert me["profile"]["nickname"] == ""


async def test_nickname_normal_ok(client):
    r = await client.patch("/api/v1/users/me", json={"nickname": "夜航的凯喵"})
    assert r.status_code == 200, r.text
    me = (await client.get("/api/v1/users/me")).json()["data"]
    assert me["profile"]["nickname"] == "夜航的凯喵"


# ───────────────────────── 进度整份快照 ─────────────────────────


def _full_snapshot(extra: dict | None = None) -> dict:
    base = {
        "theme": "dark",
        "outfit": "default",
        "doneChapters": ["cpp-ch01", "cpp-ch03"],
        "doneProjects": ["cpp-p1"],
        "checkins": ["2026-10-30", "2026-10-31"],
        "coins": 1350,
        "shards": 4,
        "answers": {"cpp-ch01-q1": {"ok": True, "at": 123}},
        "bestiary": {"cpp-ch01-q1": {"questionId": "cpp-ch01-q1", "state": "tamed", "fails": 1}},
        "chapterRuns": {"cpp-ch01": {"concept": 1, "drill": 1, "boss": 1, "attempts": 3, "lastAt": 1}},
        "weekly": {"week": "2026-W44", "claimed": False, "qids": ["cpp-ch03-q1"]},
    }
    if extra:
        base.update(extra)
    return base


async def test_progress_snapshot_roundtrip(client):
    snap = _full_snapshot()
    r = await client.put(
        "/api/v1/progress/state",
        json={"snapshot": snap, "done_chapters": snap["doneChapters"],
              "done_projects": snap["doneProjects"], "checkins": snap["checkins"],
              "coins": snap["coins"], "outfit": snap["outfit"], "theme": "dark", "client_rev": 1},
    )
    assert r.status_code == 200, r.text
    body = (await client.get("/api/v1/progress/state")).json()["data"]
    # 整份快照原样回传，含之前 Nex 会丢掉的 answers / bestiary / chapterRuns / weekly
    assert body["snapshot"] is not None
    assert body["snapshot"]["answers"] == snap["answers"]
    assert body["snapshot"]["bestiary"] == snap["bestiary"]
    assert body["snapshot"]["chapterRuns"] == snap["chapterRuns"]
    assert body["snapshot"]["weekly"] == snap["weekly"]
    # 去规范化字段同步
    assert set(body["done_chapters"]) == set(snap["doneChapters"])
    assert body["coins"] == snap["coins"]
    assert body["client_rev"] == 1


async def test_progress_snapshot_update_reflects(client):
    snap = _full_snapshot({"answers": {"cpp-ch02-q7": {"ok": True, "at": 999}}, "coins": 2000})
    r = await client.put(
        "/api/v1/progress/state",
        json={"snapshot": snap, "done_chapters": snap["doneChapters"],
              "checkins": snap["checkins"], "coins": snap["coins"], "theme": "dark", "client_rev": 2},
    )
    assert r.status_code == 200, r.text
    body = (await client.get("/api/v1/progress/state")).json()["data"]
    assert body["snapshot"]["coins"] == 2000
    assert body["snapshot"]["answers"] == snap["answers"]
    assert body["client_rev"] == 2


async def test_progress_legacy_five_fields_fallback(client):
    # 只传 5 个扁平字段（老客户端）：后端无 snapshot → 回退到历史 5 字段路径。
    # 该路径按设计做并集（换设备不丢记录），故 done_chapters / coins 会与已有值合并。
    r = await client.put(
        "/api/v1/progress/state",
        json={"done_chapters": ["legacy-ch1"], "done_projects": [], "checkins": ["2026-01-01"],
              "coins": 5, "outfit": "default", "theme": "light", "client_rev": 3},
    )
    assert r.status_code == 200, r.text
    body = (await client.get("/api/v1/progress/state")).json()["data"]
    # 关键：无 snapshot 时返回 null，前端据此走 mergeRemote 回退路径
    assert body["snapshot"] is None
    # done_chapters 走并集（含本次提交的 legacy-ch1，且不与之前快照的章节冲突）
    assert "legacy-ch1" in body["done_chapters"]
    # coins 取大（之前快照里是 2000），不会因本次小值回退
    assert body["coins"] >= 2000


async def test_progress_snapshot_rejects_non_object(client):
    r = await client.put("/api/v1/progress/state", json={"snapshot": [1, 2, 3]})
    assert r.status_code == 400, r.text


# ───────────────────────── 迁移脚本 ─────────────────────────


async def test_migration_adds_and_is_idempotent():
    """为既有库（studt_state 无 snapshot）添加列，且幂等。"""
    from scripts.migrate_add_study_state_snapshot import main as migrate_main

    # 复用本模块已建好的库：先 drop 掉 snapshot 列模拟「旧库」
    async with engine.begin() as conn:
        cols = await conn.run_sync(
            lambda c: [r["name"] for r in inspect(c).get_columns("study_state")]
        )
        assert "snapshot" in cols  # create_all 已带新列
        await conn.execute(text("ALTER TABLE study_state DROP COLUMN snapshot"))
        cols2 = await conn.run_sync(
            lambda c: [r["name"] for r in inspect(c).get_columns("study_state")]
        )
        assert "snapshot" not in cols2

    # 跑迁移：应添加列
    await migrate_main()
    async with engine.begin() as conn:
        cols3 = await conn.run_sync(
            lambda c: [r["name"] for r in inspect(c).get_columns("study_state")]
        )
        assert "snapshot" in cols3

    # 再跑一次：应幂等（已存在则跳过，不报错）
    await migrate_main()
