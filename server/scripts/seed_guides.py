# -*- coding: utf-8 -*-
"""把 content/_guides/*.json 灌入 guide_sources / guide_items（幂等 upsert）。

用法：
    python -m scripts.seed_guides --dry-run
    python -m scripts.seed_guides

幂等策略：来源以 key、条目以 slug 为准。内容来自人工整理，重复执行只会更新文本，
不会产生重复行。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent.parent
GUIDES = ROOT / "content" / "_guides"


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def load_docs() -> list[dict]:
    docs = []
    for f in sorted(GUIDES.glob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        doc["_file"] = f.name
        docs.append(doc)
    return docs


def validate(docs: list[dict]) -> list[str]:
    errs: list[str] = []
    slugs: set[str] = set()
    for doc in docs:
        src = doc.get("source") or {}
        if not src.get("repo"):
            errs.append(f"{doc['_file']}: source.repo 缺失")
        subject_keys = {s["key"] for s in (doc.get("subjects") or [])}
        if not subject_keys:
            errs.append(f"{doc['_file']}: subjects 为空")
        for it in doc.get("items") or []:
            slug = it.get("slug", "")
            if not slug:
                errs.append(f"{doc['_file']}: 有条目缺 slug")
                continue
            if slug in slugs:
                errs.append(f"{slug}: slug 跨文件重复")
            slugs.add(slug)
            if it.get("kind") not in ("note", "experience", "external"):
                errs.append(f"{slug}: kind 非法 {it.get('kind')!r}")
            if it.get("subject") not in subject_keys:
                errs.append(f"{slug}: subject {it.get('subject')!r} 不在 subjects 里")
            if not it.get("url"):
                errs.append(f"{slug}: 缺原文链接（合规要求必须可跳转）")
            if not it.get("points"):
                errs.append(f"{slug}: 要点为空，等于没提炼")
    return errs


async def seed(docs: list[dict]) -> int:
    from sqlalchemy import select

    from app.db import Base, SessionLocal, engine
    import app.models  # noqa: F401
    from app.models.enums import GuideKind
    from app.models.guide import GuideItem, GuideSource

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    src_new = src_upd = item_new = item_upd = 0
    async with SessionLocal() as db:
        for si, doc in enumerate(docs):
            # 来源 key 取文件名（11408.json → "11408"），与前端路由一致
            key = Path(doc["_file"]).stem
            src = doc.get("source") or {}
            obj = (
                await db.execute(select(GuideSource).where(GuideSource.key == key))
            ).scalar_one_or_none()
            is_new = obj is None
            if is_new:
                obj = GuideSource(key=key)
                db.add(obj)
            obj.title = src.get("title") or key
            obj.repo = src.get("repo") or ""
            obj.repo_url = src.get("repo_url") or ""
            obj.license = src.get("license")
            obj.stars = int(src.get("stars") or 0)
            obj.updated_on = parse_date(src.get("updated"))
            obj.note = doc.get("note") or ""
            obj.subjects = doc.get("subjects") or []
            obj.sort = si
            obj.is_active = True
            src_new += int(is_new)
            src_upd += int(not is_new)
            await db.flush()

            for ii, it in enumerate(doc.get("items") or []):
                obj2 = (
                    await db.execute(select(GuideItem).where(GuideItem.slug == it["slug"]))
                ).scalar_one_or_none()
                new2 = obj2 is None
                if new2:
                    obj2 = GuideItem(slug=it["slug"])
                    db.add(obj2)
                obj2.source_key = key
                obj2.kind = GuideKind(it["kind"])
                obj2.subject = it["subject"]
                obj2.title = it["title"]
                obj2.summary = it.get("summary") or ""
                obj2.points = it.get("points") or []
                obj2.read_min = int(it.get("read_min") or 5)
                obj2.recommended = bool(it.get("recommended"))
                obj2.source_path = it.get("source_path") or ""
                obj2.url = it.get("url") or ""
                obj2.sort = ii
                obj2.is_active = True
                item_new += int(new2)
                item_upd += int(not new2)
        await db.commit()

    print(f"sources: created={src_new} updated={src_upd}")
    print(f"items:   created={item_new} updated={item_upd}")
    return 0


def dry_run(docs: list[dict]) -> int:
    errs = validate(docs)
    total = sum(len(d.get("items") or []) for d in docs)
    print(f"dry-run: {len(docs)} 个来源 / {total} 条条目")
    for d in docs:
        kinds: dict[str, int] = {}
        for it in d.get("items") or []:
            kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
        print(f"  {Path(d['_file']).stem:10s} {len(d.get('items') or []):>3} 条  {kinds}")
    if errs:
        for e in errs:
            print("  -", e)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    docs = load_docs()
    sys.exit(dry_run(docs) if args.dry_run else asyncio.run(seed(docs)))
