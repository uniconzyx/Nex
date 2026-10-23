"""指南（考研笔记 / 经验贴）API。

导航逻辑：来源（source）→ 学科（subject）→ 条目（item）。
列表接口一次返回条目要点，因为单个来源体量很小（当前 18 条），
再拆详情接口只会多一次往返。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import AppError, NOT_FOUND, ok
from app.db import get_db
from app.models.enums import GuideKind
from app.models.guide import GuideItem, GuideSource

router = APIRouter(tags=["guides"])

KIND_LABEL = {
    GuideKind.note: "笔记",
    GuideKind.experience: "经验贴",
    GuideKind.external: "外部文档",
}


def _item(it: GuideItem) -> dict:
    return {
        "slug": it.slug,
        "kind": it.kind.value,
        "kind_label": KIND_LABEL.get(it.kind, it.kind.value),
        "subject": it.subject,
        "title": it.title,
        "summary": it.summary,
        "points": it.points or [],
        "read_min": it.read_min,
        "recommended": it.recommended,
        "source_path": it.source_path,
        "url": it.url,
    }


@router.get("/guides")
async def list_guides(db: AsyncSession = Depends(get_db)):
    """导航条：有哪些来源、各多少条、更新到什么时候。"""
    sources = (
        await db.execute(
            select(GuideSource)
            .where(GuideSource.deleted_at.is_(None), GuideSource.is_active.is_(True))
            .order_by(GuideSource.sort.asc())
        )
    ).scalars().all()

    rows = (
        await db.execute(
            select(GuideItem.source_key, GuideItem.kind, func.count(GuideItem.id))
            .where(GuideItem.deleted_at.is_(None), GuideItem.is_active.is_(True))
            .group_by(GuideItem.source_key, GuideItem.kind)
        )
    ).all()

    counts: dict[str, dict[str, int]] = {}
    for key, kind, n in rows:
        slot = counts.setdefault(key, {})
        slot[kind.value] = n
        slot["total"] = slot.get("total", 0) + n

    return ok({
        "sources": [
            {
                "key": s.key,
                "title": s.title,
                "repo": s.repo,
                "repo_url": s.repo_url,
                "license": s.license,
                "stars": s.stars,
                "updated_on": s.updated_on.isoformat() if s.updated_on else None,
                "note": s.note,
                "counts": counts.get(s.key, {"total": 0}),
            }
            for s in sources
        ]
    })


@router.get("/guides/{source_key}")
async def guide_detail(
    source_key: str,
    subject: str | None = Query(None, description="学科键，如 cs408 / math"),
    kind: GuideKind | None = Query(None, description="条目形态"),
    db: AsyncSession = Depends(get_db),
):
    src = (
        await db.execute(select(GuideSource).where(GuideSource.key == source_key))
    ).scalar_one_or_none()
    if src is None or src.deleted_at is not None:
        raise AppError(NOT_FOUND, "指南来源不存在", http_status=404)

    labels = {s.get("key"): s.get("label") for s in (src.subjects or []) if isinstance(s, dict)}

    conds = [
        GuideItem.source_key == source_key,
        GuideItem.deleted_at.is_(None),
        GuideItem.is_active.is_(True),
    ]
    if subject:
        conds.append(GuideItem.subject == subject)
    if kind:
        conds.append(GuideItem.kind == kind)

    items = (
        await db.execute(select(GuideItem).where(*conds).order_by(GuideItem.sort.asc()))
    ).scalars().all()

    # 学科分面按全量算，不受当前筛选影响，否则切一次学科导航就塌了
    facet_rows = (
        await db.execute(
            select(GuideItem.subject, func.count(GuideItem.id))
            .where(
                GuideItem.source_key == source_key,
                GuideItem.deleted_at.is_(None),
                GuideItem.is_active.is_(True),
            )
            .group_by(GuideItem.subject)
        )
    ).all()

    return ok({
        "source": {
            "key": src.key,
            "title": src.title,
            "repo": src.repo,
            "repo_url": src.repo_url,
            "license": src.license,
            "stars": src.stars,
            "updated_on": src.updated_on.isoformat() if src.updated_on else None,
            "note": src.note,
        },
        "subjects": [
            {"key": s, "label": labels.get(s, s), "count": n}
            for s, n in sorted(facet_rows, key=lambda r: -r[1])
        ],
        "items": [_item(i) for i in items],
        "total": len(items),
    })
