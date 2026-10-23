# -*- coding: utf-8 -*-
"""把 content/_projects/career-projects.json 灌入数据库（幂等 upsert）。

数据流：
    content/_projects/career/<track>.json   （人工撰写，按学科分片）
        └─ scripts.build_career_library      → career-projects.json（含 GitHub 实测元数据）
            └─ 本脚本                        → career_projects / career_project_steps / career_routes

用法：
    python -m scripts.seed_career_projects            # 写库
    python -m scripts.seed_career_projects --dry-run  # 只解析校验，不连库

幂等策略：项目以 slug、路线以 key 为准。已存在则更新字段并重建 steps
（steps 是只读内容，重建最省心）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "content" / "_projects" / "career-projects.json"
PLAN = ROOT / "content" / "_projects" / "career-plan.json"


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def load_items() -> list[dict]:
    doc = json.loads(DATA.read_text(encoding="utf-8"))
    return doc["items"]


def load_routes() -> list[dict]:
    if not PLAN.exists():
        return []
    doc = json.loads(PLAN.read_text(encoding="utf-8"))
    return doc.get("routes") or []


async def seed() -> int:
    from sqlalchemy import delete, select

    from app.db import Base, SessionLocal, engine
    import app.models  # noqa: F401
    from app.models.career import CareerProject, CareerProjectStep, CareerRoute
    from app.models.enums import CareerTrack, Difficulty, ProjectTier

    items = load_items()
    routes = load_routes()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    created = updated = 0
    async with SessionLocal() as db:
        for idx, it in enumerate(items):
            meta = it.get("meta", {})
            track = CareerTrack(it["track"])
            level = Difficulty(it["level"])
            tier = ProjectTier(it["tier"])

            obj = (
                await db.execute(select(CareerProject).where(CareerProject.slug == it["slug"]))
            ).scalar_one_or_none()
            is_new = obj is None
            if is_new:
                obj = CareerProject(slug=it["slug"])
                db.add(obj)

            obj.track = track
            obj.title = it["title"]
            obj.repo = it["repo"]
            obj.repo_url = meta.get("repo_url") or f"https://github.com/{it['repo']}"
            obj.summary = it["summary"]
            obj.level = level
            obj.tier = tier
            obj.hours = int(it.get("hours") or 0)
            obj.stack = it["stack"]
            obj.learn = it["learn"]
            obj.career_value = it["career"]
            obj.accept = it["accept"]
            obj.interview = it["interview"]
            obj.stars = int(meta.get("stars") or 0)
            obj.forks = int(meta.get("forks") or 0)
            obj.language = meta.get("language")
            obj.license = meta.get("license")
            obj.last_pushed = parse_date(meta.get("pushed"))
            obj.size_kb = int(meta.get("size_kb") or 0)
            obj.archived = bool(meta.get("archived"))
            obj.repo_desc = meta.get("desc") or ""
            obj.topics = meta.get("topics") or []
            obj.open_issues = int(meta.get("open_issues") or 0)
            obj.sort = idx
            obj.is_active = True
            await db.flush()

            # 重建步骤
            await db.execute(
                delete(CareerProjectStep).where(CareerProjectStep.project_id == obj.id)
            )
            for i, step in enumerate(it["steps"]):
                db.add(CareerProjectStep(
                    project_id=obj.id,
                    order_no=i,
                    title=step,
                    description="",
                    verification={},
                ))

            if is_new:
                created += 1
            else:
                updated += 1
        await db.commit()

        route_new = route_upd = 0
        for i, r in enumerate(routes):
            obj = (
                await db.execute(select(CareerRoute).where(CareerRoute.key == r["key"]))
            ).scalar_one_or_none()
            is_new = obj is None
            if is_new:
                obj = CareerRoute(key=r["key"])
                db.add(obj)
            obj.title = r["title"]
            obj.summary = r.get("summary") or ""
            obj.tracks = r.get("tracks") or {}
            obj.t4_required = int(r.get("t4_required") or 0)
            obj.projects = int(r.get("projects") or 0)
            obj.hours = int(r.get("hours") or 0)
            obj.deliverables = r.get("deliverables") or []
            obj.interview_bar = r.get("interview_bar") or []
            obj.sort = i
            obj.is_active = True
            if is_new:
                route_new += 1
            else:
                route_upd += 1
        await db.commit()

    print(f"projects: created={created} updated={updated} total={len(items)}")
    print(f"routes:   created={route_new} updated={route_upd} total={len(routes)}")
    return 0


def dry_run() -> int:
    items = load_items()
    routes = load_routes()
    errors: list[str] = []
    for it in items:
        meta = it.get("meta") or {}
        if not meta.get("repo_url"):
            errors.append(f"{it['slug']}: 缺少 meta，请先跑 build_career_library")
        if len(it["steps"]) < 3:
            errors.append(f"{it['slug']}: 步骤少于 3 条")
        if len(it["learn"]) < 3:
            errors.append(f"{it['slug']}: 学习点少于 3 条")
        if len(it["accept"]) < 3:
            errors.append(f"{it['slug']}: 验收标准少于 3 条")
        if it.get("tier") not in ("t1", "t2", "t3", "t4"):
            errors.append(f"{it['slug']}: tier 非法 {it.get('tier')!r}")
        if not isinstance(it.get("hours"), int) or it["hours"] <= 0:
            errors.append(f"{it['slug']}: hours 非法 {it.get('hours')!r}")
        parse_date(meta.get("pushed"))
    for r in routes:
        if not r.get("tracks"):
            errors.append(f"route {r.get('key')}: 未声明学科要求")
        if int(r.get("t4_required") or 0) > 3:
            errors.append(f"route {r.get('key')}: t4_required 不合理")
    print(f"dry-run: {len(items)} 条目 / {len(routes)} 条路线解析完成")
    if errors:
        for e in errors:
            print("  -", e)
        return 1
    tracks = sorted({it["track"] for it in items})
    print(f"覆盖学科 {len(tracks)}: {', '.join(tracks)}")
    tier_cnt = Counter(it.get("tier") for it in items)
    print("梯度分布:", {k: tier_cnt.get(k, 0) for k in ("t1", "t2", "t3", "t4")})
    print(f"总工时: {sum(it.get('hours') or 0 for it in items)}h")
    per_track = Counter(it["track"] for it in items)
    print("每学科:", dict(sorted(per_track.items())))
    print("OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.exit(dry_run() if args.dry_run else asyncio.run(seed()))
