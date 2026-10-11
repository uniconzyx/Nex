import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Chapter
from app.models.enums import Difficulty, ExerciseType, ResourceSource, ResourceType
from app.models.exercise import Exercise, Tag, TestCase
from app.models.resource import Resource, resource_chapters
from app.services.sync.schemas import ExercisePackage, ExternalPackage

_DIFF = {"easy": Difficulty.easy, "mid": Difficulty.mid, "hard": Difficulty.hard}
_SRC = {"leetcode": ResourceSource.leetcode, "nowcoder": ResourceSource.nowcoder,
        "github": ResourceSource.github, "doc": ResourceSource.doc}


async def import_package(db: AsyncSession, raw: str) -> dict:
    """识别包类型 → 全量校验（任何一条非法则整包拒绝）→ 事务落库。"""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"非法 JSON：{exc}") from exc
    fmt = (payload.get("meta") or {}).get("format", "")
    if fmt == "cppmind-external-v1":
        pkg = ExternalPackage.model_validate(payload)
        return await _import_external(db, pkg)
    if fmt == "cppmind-exercise-v1":
        pkg = ExercisePackage.model_validate(payload)
        return await _import_exercises(db, pkg)
    raise ValueError("无法识别的包格式（meta.format 缺失或未知）")


async def _import_external(db: AsyncSession, pkg: ExternalPackage) -> dict:
    source = _SRC[pkg.meta["source"]]
    chapter_by_code = {
        c.code: c for c in (await db.execute(select(Chapter))).scalars().all()
    }
    created = updated = 0
    async with db.begin_nested():
        for item in pkg.items:
            existing = (
                await db.execute(
                    select(Resource).where(Resource.source == source,
                                           Resource.external_id == item.external_id)
                )
            ).scalar_one_or_none()
            fields = {
                "title": item.title, "title_cn": item.title_cn, "url": item.url,
                "difficulty": _DIFF.get(item.difficulty or "", None),
                "extra": {"tags": item.tags},
            }
            if existing is None:
                existing = Resource(
                    source=source,
                    type=ResourceType.problem if source != ResourceSource.github else ResourceType.repo,
                    external_id=item.external_id, **fields,
                )
                db.add(existing)
                await db.flush()
                created += 1
            else:
                for k, v in fields.items():
                    setattr(existing, k, v)
                updated += 1
            for code in item.mapped_chapters:
                chapter = chapter_by_code.get(code)
                if chapter is None:
                    raise ValueError(f"映射章节不存在：{code}")
                link = await db.execute(
                    select(resource_chapters).where(
                        resource_chapters.c.resource_id == existing.id,
                        resource_chapters.c.chapter_id == chapter.id,
                    )
                )
                if link.first() is None:
                    await db.execute(resource_chapters.insert().values(
                        resource_id=existing.id, chapter_id=chapter.id))
    await db.commit()
    return {"created": created, "updated": updated, "type": "external"}


async def _import_exercises(db: AsyncSession, pkg: ExercisePackage) -> dict:
    chapter = (
        await db.execute(select(Chapter).where(Chapter.code == pkg.meta["chapter"]))
    ).scalar_one_or_none()
    if chapter is None:
        raise ValueError(f"章节不存在：{pkg.meta['chapter']}")

    tag_cache: dict[str, Tag] = {}
    created = 0
    async with db.begin_nested():
        for item in pkg.items:
            exercise = Exercise(
                chapter_id=chapter.id, type=ExerciseType(item.type),
                difficulty=_DIFF.get(item.difficulty, Difficulty.mid),
                title=item.title, content_md=item.content_md, options=item.options,
                answer=item.answer, explanation=item.explanation,
                time_limit_ms=item.time_limit_ms, memory_limit_mb=item.memory_limit_mb,
            )
            db.add(exercise)
            await db.flush()
            for tc in item.test_cases:
                db.add(TestCase(exercise_id=exercise.id, input=tc.input,
                                expected_output=tc.expected_output, is_sample=tc.is_sample))
            for tag_name in item.tags:
                if tag_name not in tag_cache:
                    tag = (await db.execute(select(Tag).where(Tag.name == tag_name))).scalar_one_or_none()
                    if tag is None:
                        tag = Tag(name=tag_name)
                        db.add(tag)
                        await db.flush()
                    tag_cache[tag_name] = tag
                exercise.tags.append(tag_cache[tag_name])
            created += 1
    await db.commit()
    return {"created": created, "type": "exercise", "chapter": chapter.code}
