import yaml
import httpx
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Chapter
from app.models.enums import ResourceSource, ResourceType
from app.models.resource import Resource, resource_chapters


def load_repo_map() -> dict:
    """shared/schemas/github_repos.yaml：{ chapter_code: [owner/repo, ...] }"""
    path = Path(settings.shared_dir) / "schemas" / "github_repos.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


async def sync_github(db: AsyncSession, mode: str = "incremental") -> dict:
    """按章节映射同步 GitHub 仓库元数据（描述/star/许可证）。只存元数据 + 链接。"""
    repo_map = load_repo_map()
    stats = {"created": 0, "updated": 0, "failed": 0}
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    chapter_rows = (await db.execute(select(Chapter))).scalars().all()
    chapter_by_code = {c.code: c for c in chapter_rows}

    async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=30) as client:
        for chapter_code, repos in repo_map.items():
            chapter = chapter_by_code.get(chapter_code)
            if chapter is None:
                continue
            for full_name in repos:
                ext_id = f"github:{full_name}"
                try:
                    resp = await client.get(f"/repos/{full_name}")
                    resp.raise_for_status()
                    info = resp.json()
                except Exception:
                    stats["failed"] += 1
                    continue

                existing = (
                    await db.execute(
                        select(Resource).where(
                            Resource.source == ResourceSource.github,
                            Resource.external_id == ext_id,
                        )
                    )
                ).scalar_one_or_none()

                fields = {
                    "title": info.get("full_name", full_name),
                    "description": (info.get("description") or "")[:2000],
                    "url": info.get("html_url", f"https://github.com/{full_name}"),
                    "stars": info.get("stargazers_count", 0),
                    "license": (info.get("license") or {}).get("spdx_id"),
                    "extra": {"topics": info.get("topics", []), "language": info.get("language")},
                    "last_synced_at": datetime.now(UTC),
                }
                if existing is None:
                    existing = Resource(
                        source=ResourceSource.github, type=ResourceType.repo,
                        external_id=ext_id, **fields,
                    )
                    db.add(existing)
                    await db.flush()
                    stats["created"] += 1
                else:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                    stats["updated"] += 1

                # 章节关联（幂等）
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
