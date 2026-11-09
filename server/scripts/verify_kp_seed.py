#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在真 Postgres 上端到端验收 knowledge_points 播种（不需要 Docker）。

跑什么
--------------------------------------------------------------------
1. 起临时 embedded PG（或注入 DATABASE_URL 直连外部库）；
2. 建表 → `init_db`（内部已含一次 seed）→ 再跑一次 seed 验幂等；
3. 造一个用户 + 一条 Progress，证明掌握度不是恒 0；
4. 用 httpx ASGITransport 直接打 FastAPI app，验收 6 个内容接口真的有数据：
   courses / chapters(mastery_avg) / chapter_detail(coverage) /
   lessons(全文) / mindmap(节点) / search(kp 命中) / PATCH mastery。

用法：cd server && python -m scripts.verify_kp_seed
外部库：DATABASE_URL=postgresql://... python -m scripts.verify_kp_seed
（注入外部库时**不会** drop_all，只补表；默认临时库才会重建。）
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_ROOT))
os.chdir(SERVER_ROOT)  # 让 .env 能被 config 读到

EXTERNAL = os.environ.get("DATABASE_URL")
EMBEDDED = not EXTERNAL
if EMBEDDED:
    import embedded_postgres as ep

    PGDATA = os.environ.get("EMBEDDED_PG_PGDATA", "D:/WB_Workspace/_tmp_pg_kpseed/pgdata")
    Path(PGDATA).parent.mkdir(parents=True, exist_ok=True)
    _srv = ep.get_server(pgdata=PGDATA, cleanup_mode="stop")
    _srv.ensure_pgdata_inited()
    _srv.ensure_postgres_running()
    uri = _srv.get_uri()
else:
    uri = EXTERNAL.replace("postgresql+asyncpg://", "postgresql://")  # type: ignore[union-attr]
os.environ["DATABASE_URL"] = uri.replace("postgresql://", "postgresql+asyncpg://")

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

import app.models  # noqa: F401,E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.content import Chapter, Course, KnowledgePoint, Lesson, MindMapNode  # noqa: E402
from app.models.progress import Progress  # noqa: E402
from app.models.user import User  # noqa: E402
from scripts.init_db import main as init_db_main  # noqa: E402
from scripts.seed_knowledge_points import collect, seed  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASSED if cond else FAILED).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")


async def main() -> None:
    print(f"[db] DATABASE_URL={os.environ['DATABASE_URL']}")
    if EMBEDDED:
        async with engine.begin() as c:
            await c.run_sync(Base.metadata.drop_all)
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    # 造一个用户（get_current_user 需要账号是 active）。
    # CI 里本脚本排在 verify_nex_parity_pg 之后：parity 显式插 User.id=1..4，
    # 但 PostgreSQL 的序列不会因此前进，自动分配 id 会撞 users_pkey。
    # 所以按 email 复用 / 显式取 max(id)+1，单独跑（空库）时同样成立。
    from sqlalchemy import func as sa_func

    async with SessionLocal() as db:
        existing = (
            await db.execute(select(User).where(User.email == "kpseed@verify.dev"))
        ).scalar_one_or_none()
        if existing is not None:
            uid = existing.id
        else:
            max_id = (await db.execute(select(sa_func.max(User.id)))).scalar_one() or 0
            user = User(
                id=max_id + 1,
                email="kpseed@verify.dev",
                password_hash=hash_password("x"),
            )
            db.add(user)
            await db.commit()
            uid = user.id
    token = create_access_token(uid)
    headers = {"Authorization": f"Bearer {token}"}

    # ① 建库 + 播种（init_db 内部会调一次 seed）
    await init_db_main()
    # ② 再跑一次：所有计数必须是 0
    again = await seed()
    check("二次播种幂等", all(v == 0 for v in again.values()), str(again))
    # ③ --check 口径：0 缺失
    verdict = await seed(check_only=True)
    check("完整性检查", verdict.get("missing") == 0, str(verdict))

    packs = collect()
    want_ch = sum(len(v) for v in packs.values())
    want_docs = sum(len(d) for v in packs.values() for d in v.values())

    async with SessionLocal() as db:
        courses = (await db.execute(select(Course))).scalars().all()
        chapters = (await db.execute(select(Chapter))).scalars().all()
        kps = (await db.execute(select(KnowledgePoint))).scalars().all()
        lessons = (await db.execute(select(Lesson))).scalars().all()
        nodes = (await db.execute(select(MindMapNode))).scalars().all()
        cpp = (await db.execute(select(Course).where(Course.code == "cpp"))).scalar_one()
        ch1 = (await db.execute(select(Chapter).where(Chapter.code == "cpp-ch01"))).scalar_one()
        kp1 = (
            await db.execute(select(KnowledgePoint).where(KnowledgePoint.chapter_id == ch1.id).order_by(KnowledgePoint.sort))
        ).scalars().first()

        check("学科 16 门", len(courses) == 16, f"={len(courses)}")
        check("章节 167 章（无孤儿）", len(chapters) == want_ch, f"={len(chapters)}")
        check("知识点 723 条", len(kps) == want_docs, f"={len(kps)}")
        check("概念课文 723 篇（带全文）", len(lessons) == want_docs, f"={len(lessons)}")
        check("导图节点 = 167 根 + 723 概念", len(nodes) == want_ch + want_docs, f"={len(nodes)}")
        check("KP 摘要非空", all(k.summary for k in kps), f"空={sum(1 for k in kps if not k.summary)}")
        check("课文非空", all(l.content_md for l in lessons), f"空={sum(1 for l in lessons if not l.content_md)}")

        # 给一个 KP 记掌握度 3（精通），验证 mastery_avg 不再是恒 0。
        # 幂等：重复跑同一库时只更新，不撞 uq_progress_user_kp。
        prog = (
            await db.execute(
                select(Progress).where(Progress.user_id == uid, Progress.kp_id == kp1.id)
            )
        ).scalar_one_or_none()
        if prog is None:
            db.add(Progress(user_id=uid, kp_id=kp1.id, mastery=3))
        else:
            prog.mastery = 3
        await db.commit()
        cpp_id, ch1_id, kp1_id, kp1_title = cpp.id, ch1.id, kp1.id, kp1.title

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://verify") as client:
        r = await client.get("/api/v1/courses")
        body = r.json()
        check("GET /courses 返回 16 门", r.status_code == 200 and len(body.get("data", [])) == 16,
              f"status={r.status_code} n={len(body.get('data', []))}")

        r = await client.get("/api/v1/chapters", params={"course_id": cpp_id}, headers=headers)
        rows = r.json().get("data", [])
        avg = next((x["mastery_avg"] for x in rows if x["code"] == "cpp-ch01"), None)
        check("GET /chapters mastery_avg 非 0", r.status_code == 200 and avg is not None and avg > 0,
              f"status={r.status_code} cpp-ch01={avg} n={len(rows)}")

        r = await client.get(f"/api/v1/chapters/{ch1_id}", headers=headers)
        cov = r.json().get("data", {}).get("coverage", {})
        check("GET /chapters/{id} coverage.concepts 非 0", r.status_code == 200 and cov.get("concepts", 0) > 0,
              f"status={r.status_code} coverage={cov}")

        r = await client.get(f"/api/v1/chapters/{ch1_id}/lessons", params={"type": "concept"}, headers=headers)
        ls = r.json().get("data", [])
        longest = max((len(x.get("content_md", "")) for x in ls), default=0)
        check("GET /lessons?type=concept 返回全文", r.status_code == 200 and len(ls) > 0 and longest > 1000,
              f"status={r.status_code} n={len(ls)} longest={longest}")

        r = await client.get(f"/api/v1/chapters/{ch1_id}/mindmap", headers=headers)
        ns = r.json().get("data", {}).get("nodes", [])
        kp_nodes = [n for n in ns if n.get("kp_id")]
        check("GET /mindmap 节点含 kp_id", r.status_code == 200 and len(kp_nodes) > 0,
              f"status={r.status_code} nodes={len(ns)} kp_nodes={len(kp_nodes)}")

        q = kp1_title[:2] or "概念"
        r = await client.get("/api/v1/search", params={"q": q}, headers=headers)
        items = r.json().get("data", {}).get("items", [])
        check("GET /search 命中知识点", r.status_code == 200 and any(i.get("kind") == "kp" for i in items),
              f"status={r.status_code} q={q!r} items={len(items)}")

        r = await client.patch(f"/api/v1/knowledge-points/{kp1_id}/mastery",
                               json={"mastery": 2}, headers=headers)
        check("PATCH /knowledge-points/{id}/mastery", r.status_code == 200 and r.json().get("code") == 0,
              f"status={r.status_code} body={str(r.json())[:120]}")

    print(f"\nRESULT: {len(PASSED)} PASS / {len(FAILED)} FAIL")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        raise SystemExit(1)
    print("KP_SEED_VERIFY_OK")


if __name__ == "__main__":
    asyncio.run(main())
