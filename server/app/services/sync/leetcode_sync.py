import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Chapter
from app.models.enums import Difficulty, ResourceSource, ResourceType
from app.models.resource import Resource, resource_chapters

_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleCn: translatedTitle
    titleSlug
    difficulty
    topicTags { slug }
  }
}
"""

_DIFF_MAP = {"Easy": Difficulty.easy, "Medium": Difficulty.mid, "Hard": Difficulty.hard}


def load_leetcode_map() -> list[dict]:
    """shared/schemas/leetcode_map.json：章节→题目 slug 映射（合规：只用元数据）。"""
    path = Path(settings.shared_dir) / "schemas" / "leetcode_map.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("mappings", [])


async def sync_leetcode(db: AsyncSession, mode: str = "incremental") -> dict:
    """GraphQL 拉取题目元数据（题号/标题/难度/标签/链接），不存题面正文。"""
    mappings = load_leetcode_map()
    stats = {"created": 0, "updated": 0, "failed": 0}

    chapter_rows = (await db.execute(select(Chapter))).scalars().all()
    chapter_by_code = {c.code: c for c in chapter_rows}

    async with httpx.AsyncClient(timeout=30) as client:
        for item in mappings:
            slug = item.get("slug")
            if not slug:
                continue
            ext_id = f"leetcode:{slug}"
            try:
                resp = await client.post(
                    settings.leetcode_graphql,
                    json={"query": _QUERY, "variables": {"titleSlug": slug}},
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                q = (resp.json().get("data") or {}).get("question")
                if not q:
                    stats["failed"] += 1
                    continue
            except Exception:
                stats["failed"] += 1
                continue

            fields = {
                "title": q["title"],
                "title_cn": q.get("titleCn"),
                "url": f"https://leetcode.cn/problems/{slug}/",
                "difficulty": _DIFF_MAP.get(q.get("difficulty", ""), None),
                "extra": {
                    "frontend_id": q.get("questionFrontendId"),
                    "tags": [t["slug"] for t in q.get("topicTags", [])],
                },
                "last_synced_at": datetime.now(UTC),
            }
            existing = (
                await db.execute(
                    select(Resource).where(
                        Resource.source == ResourceSource.leetcode,
                        Resource.external_id == ext_id,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                existing = Resource(
                    source=ResourceSource.leetcode, type=ResourceType.problem,
                    external_id=ext_id, **fields,
                )
                db.add(existing)
                await db.flush()
                stats["created"] += 1
            else:
                for k, v in fields.items():
                    setattr(existing, k, v)
                stats["updated"] += 1

            for code in item.get("mapped_chapters", []):
                chapter = chapter_by_code.get(code)
                if chapter is None:
                    continue
                link = await db.execute(
                    select(resource_chapters).where(
                        resource_chapters.c.resource_id == existing.id,
                        resource_chapters.c.chapter_id == chapter.id,
                    )
                )
                if link.first() is None:
                    await db.execute(
                        resource_chapters.insert().values(
                            resource_id=existing.id, chapter_id=chapter.id
                        )
                    )
    await db.commit()
    return stats
