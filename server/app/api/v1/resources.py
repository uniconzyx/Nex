import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.responses import ok, page_data
from app.db import get_db
from app.models.content import Chapter
from app.models.enums import ResourceSource, ResourceType
from app.models.resource import Resource, resource_chapters

router = APIRouter(tags=["resources"])


@router.get("/resources")
async def list_resources(
    source: ResourceSource | None = None,
    type: ResourceType | None = None,
    chapter_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    conds = []
    if source:
        conds.append(Resource.source == source)
    if type:
        conds.append(Resource.type == type)
    if chapter_id:
        conds.append(Resource.id.in_(
            select(resource_chapters.c.resource_id)
            .where(resource_chapters.c.chapter_id == chapter_id)
        ))
    query = select(Resource).where(*conds)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        await db.execute(query.order_by(Resource.stars.desc().nulls_last(), Resource.id)
                         .offset((page - 1) * size).limit(size))
    ).scalars().all()
    items = [
        {
            "id": r.id, "source": r.source.value, "type": r.type.value,
            "title": r.title, "title_cn": r.title_cn, "description": r.description,
            "url": r.url, "stars": r.stars, "license": r.license,
            "difficulty": r.difficulty.value if r.difficulty else None,
            "extra": r.extra, "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
        }
        for r in rows
    ]
    return ok(page_data(items, total, page, size))


@router.get("/resources/leetcode-map")
async def leetcode_map(db: AsyncSession = Depends(get_db)):
    """章节→LeetCode 题目映射表（从 DB 聚合，跳原站）。"""
    rows = (
        await db.execute(
            select(Chapter.code, Chapter.title, Resource)
            .join(resource_chapters, resource_chapters.c.chapter_id == Chapter.id)
            .join(Resource, Resource.id == resource_chapters.c.resource_id)
            .where(Resource.source == ResourceSource.leetcode)
            .order_by(Chapter.idx)
        )
    ).all()
    grouped: dict[str, dict] = {}
    for code, title, r in rows:
        g = grouped.setdefault(code, {"chapter_code": code, "chapter_title": title, "problems": []})
        g["problems"].append({
            "external_id": r.external_id, "title": r.title, "title_cn": r.title_cn,
            "difficulty": r.difficulty.value if r.difficulty else None, "url": r.url,
        })
    return ok(list(grouped.values()))
