from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_optional_user
from app.core.responses import AppError, NOT_FOUND, ok, page_data
from app.db import get_db
from app.models.enums import Difficulty, ExerciseSource, ExerciseType
from app.models.exercise import Exercise, InterviewQuestion, Tag, exercise_tags
from app.models.user import User

router = APIRouter(tags=["exercises"])


@router.get("/exercises")
async def list_exercises(
    chapter_id: int | None = None,
    type: ExerciseType | None = None,
    difficulty: Difficulty | None = None,
    tag: str | None = None,
    source: ExerciseSource | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    conds = []
    if chapter_id:
        conds.append(Exercise.chapter_id == chapter_id)
    if type:
        conds.append(Exercise.type == type)
    if difficulty:
        conds.append(Exercise.difficulty == difficulty)
    if source:
        conds.append(Exercise.source == source)
    if tag:
        conds.append(Exercise.id.in_(
            select(exercise_tags.c.exercise_id).join(Tag, Tag.id == exercise_tags.c.tag_id)
            .where(Tag.name == tag)
        ))
    query = select(Exercise).where(*conds)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        await db.execute(query.order_by(Exercise.id).offset((page - 1) * size).limit(size))
    ).scalars().all()
    items = [
        {
            "id": e.id, "chapter_id": e.chapter_id, "type": e.type.value,
            "difficulty": e.difficulty.value, "title": e.title,
            "source": e.source.value, "external_url": e.external_url,
        }
        for e in rows
    ]
    return ok(page_data(items, total, page, size))


@router.get("/exercises/daily")
async def daily_exercise(db: AsyncSession = Depends(get_db)):
    """每日一题：按日期确定性选取。"""
    rows = (
        await db.execute(select(Exercise.id).where(Exercise.is_daily_eligible.is_(True)))
    ).scalars().all()
    if not rows:
        return ok(None, "暂无可用的每日一题")
    pick = rows[datetime.now(UTC).toordinal() % len(rows)]
    e = await db.get(Exercise, pick)
    return ok({"id": e.id, "title": e.title, "type": e.type.value, "difficulty": e.difficulty.value})


@router.get("/exercises/{exercise_id}")
async def exercise_detail(
    exercise_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    e = await db.get(Exercise, exercise_id)
    if e is None:
        raise AppError(NOT_FOUND, "题目不存在", http_status=404)
    # 非示例测试用例不下发（防作弊）
    sample_cases = [
        {"input": tc.input, "expected_output": tc.expected_output}
        for tc in e.test_cases if tc.is_sample
    ]
    return ok({
        "id": e.id, "chapter_id": e.chapter_id, "type": e.type.value,
        "difficulty": e.difficulty.value, "title": e.title, "content_md": e.content_md,
        "options": e.options, "sample_cases": sample_cases,
        "time_limit_ms": e.time_limit_ms, "memory_limit_mb": e.memory_limit_mb,
        "source": e.source.value, "external_url": e.external_url,
        # 登录后才返回答案与解析
        "answer": e.answer if user else None,
        "explanation": e.explanation if user else None,
    })


@router.get("/interview-questions")
async def list_interview_questions(
    chapter_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    conds = [InterviewQuestion.chapter_id == chapter_id] if chapter_id else []
    query = select(InterviewQuestion).where(*conds)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    rows = (
        await db.execute(query.order_by(InterviewQuestion.id).offset((page - 1) * size).limit(size))
    ).scalars().all()
    items = [
        {
            "id": q.id, "chapter_id": q.chapter_id, "question": q.question,
            "answer_md": q.answer_md, "follow_ups": q.follow_ups,
            "difficulty": q.difficulty.value, "company_tags": q.company_tags,
        }
        for q in rows
    ]
    return ok(page_data(items, total, page, size))
