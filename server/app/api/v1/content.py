from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_optional_user, guard_chapter_access
from app.core.responses import AppError, NOT_FOUND, ok, page_data
from app.db import get_db
from app.models.content import (
    Chapter,
    Course,
    DeepLearningModule,
    KnowledgePoint,
    Lesson,
    MindMapNode,
)
from app.models.enums import LessonType
from app.models.exercise import Exercise, InterviewQuestion
from app.models.progress import Progress
from app.models.submission import Submission
from app.models.user import User
from app.schemas.content import MasteryPatch
from app.services.mindmap import derive_node_state

router = APIRouter(tags=["content"])


async def _get_chapter_or_404(db: AsyncSession, chapter_id: int) -> Chapter:
    ch = await db.get(Chapter, chapter_id)
    if ch is None or ch.deleted_at is not None:
        raise AppError(NOT_FOUND, "章节不存在", http_status=404)
    return ch


@router.get("/courses")
async def list_courses(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Course).order_by(Course.sort))).scalars().all()
    return ok([{"id": c.id, "code": c.code, "title": c.title, "description": c.description} for c in rows])


@router.get("/chapters")
async def list_chapters(
    course_id: int = Query(...),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    chapters = (
        await db.execute(
            select(Chapter).where(Chapter.course_id == course_id, Chapter.deleted_at.is_(None))
            .order_by(Chapter.idx)
        )
    ).scalars().all()

    mastery_map: dict[int, float] = {}
    if user is not None:
        rows = await db.execute(
            select(KnowledgePoint.chapter_id, func.avg(Progress.mastery))
            .join(Progress, Progress.kp_id == KnowledgePoint.id)
            .where(Progress.user_id == user.id)
            .group_by(KnowledgePoint.chapter_id)
        )
        mastery_map = {cid: float(avg) for cid, avg in rows}

    return ok([
        {
            "id": c.id, "code": c.code, "idx": c.idx, "title": c.title,
            "is_free": c.is_free, "estimated_minutes": c.estimated_minutes,
            "mastery_avg": round(mastery_map.get(c.id, 0.0), 2),
            "locked": user is None and not c.is_free,
        }
        for c in chapters
    ])


@router.get("/chapters/{chapter_id}")
async def chapter_detail(
    chapter_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    ch = await _get_chapter_or_404(db, chapter_id)
    guard_chapter_access(ch.is_free, user)

    async def count(model, *conds):
        return (await db.execute(
            select(func.count()).select_from(model).where(*conds)
        )).scalar_one()

    # 7 类内容索引（PRD 验收对照）
    coverage = {
        "goals": ch.goals,
        "concepts": await count(Lesson, Lesson.chapter_id == ch.id, Lesson.type == LessonType.concept),
        "pitfalls": await count(Lesson, Lesson.chapter_id == ch.id, Lesson.type == LessonType.pitfall),
        "examples": await count(Lesson, Lesson.chapter_id == ch.id, Lesson.type == LessonType.example),
        "exercises": await count(Exercise, Exercise.chapter_id == ch.id),
        "interview_questions": await count(InterviewQuestion, InterviewQuestion.chapter_id == ch.id),
    }
    return ok({
        "id": ch.id, "code": ch.code, "idx": ch.idx, "title": ch.title,
        "goals": ch.goals, "estimated_minutes": ch.estimated_minutes, "coverage": coverage,
    })


@router.get("/chapters/{chapter_id}/lessons")
async def chapter_lessons(
    chapter_id: int,
    type: LessonType | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    ch = await _get_chapter_or_404(db, chapter_id)
    guard_chapter_access(ch.is_free, user)
    conds = [Lesson.chapter_id == ch.id, Lesson.deleted_at.is_(None)]
    if type:
        conds.append(Lesson.type == type)
    rows = (
        await db.execute(select(Lesson).where(*conds).order_by(Lesson.sort))
    ).scalars().all()
    return ok([
        {
            "id": l.id, "type": l.type.value, "title": l.title, "content_md": l.content_md,
            "code": l.code, "code_lang": l.code_lang.value if l.code_lang else None,
            "code_std": l.code_std.value if l.code_std else None,
            "stdin": l.stdin, "expected_output": l.expected_output, "kp_id": l.kp_id,
        }
        for l in rows
    ])


@router.get("/chapters/{chapter_id}/mindmap")
async def chapter_mindmap(
    chapter_id: int,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    ch = await _get_chapter_or_404(db, chapter_id)
    guard_chapter_access(ch.is_free, user)
    nodes = (
        await db.execute(select(MindMapNode).where(MindMapNode.chapter_id == ch.id).order_by(MindMapNode.sort))
    ).scalars().all()

    mastery_by_kp: dict[int, int] = {}
    weak_kps: set[int] = set()
    if user is not None:
        prog = (
            await db.execute(
                select(Progress).join(KnowledgePoint, KnowledgePoint.id == Progress.kp_id)
                .where(Progress.user_id == user.id, KnowledgePoint.chapter_id == ch.id)
            )
        ).scalars().all()
        mastery_by_kp = {p.kp_id: p.mastery for p in prog}

        # 薄弱判定：该章知识点关联练习的近期正确率 < 50%（近 10 次提交）
        kp_exercise_ids = (
            await db.execute(select(Exercise.id).where(Exercise.chapter_id == ch.id))
        ).scalars().all()
        if kp_exercise_ids:
            recent = (
                await db.execute(
                    select(Submission).where(
                        Submission.user_id == user.id,
                        Submission.exercise_id.in_(kp_exercise_ids),
                    ).order_by(Submission.created_at.desc()).limit(10)
                )
            ).scalars().all()
            if recent:
                ac_rate = sum(1 for s in recent if s.status.value == "ac") / len(recent)
                if ac_rate < 0.5:
                    kp_rows = (
                        await db.execute(
                            select(KnowledgePoint.id).where(KnowledgePoint.chapter_id == ch.id)
                        )
                    ).scalars().all()
                    weak_kps = set(kp_rows)

    return ok({
        "chapter_code": ch.code,
        "nodes": [
            {
                "id": n.id, "parent_id": n.parent_id, "kp_id": n.kp_id,
                "label": n.label, "x": float(n.pos_x), "y": float(n.pos_y),
                "state": derive_node_state(n.kp_id, mastery_by_kp, weak_kps),
            }
            for n in nodes
        ],
    })


@router.patch("/knowledge-points/{kp_id}/mastery")
async def set_mastery(
    kp_id: int,
    body: MasteryPatch,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import UTC, datetime

    kp = await db.get(KnowledgePoint, kp_id)
    if kp is None:
        raise AppError(NOT_FOUND, "知识点不存在", http_status=404)
    prog = (
        await db.execute(
            select(Progress).where(Progress.user_id == user.id, Progress.kp_id == kp_id)
        )
    ).scalar_one_or_none()
    if prog is None:
        prog = Progress(user_id=user.id, kp_id=kp_id, mastery=body.mastery)
        db.add(prog)
    else:
        prog.mastery = body.mastery
    prog.last_studied_at = datetime.now(UTC)
    await db.commit()
    return ok(message="已标记")


@router.get("/dl/modules")
async def dl_modules(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(DeepLearningModule).order_by(DeepLearningModule.sort))
    ).scalars().all()
    return ok([
        {
            "id": m.id, "chapter_id": m.chapter_id, "type": m.type.value,
            "framework": m.framework.value if m.framework else None,
            "content_md": m.content_md,
        }
        for m in rows
    ])


@router.get("/search")
async def search(
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    like = f"%{q}%"
    kp_rows = (
        await db.execute(
            select(KnowledgePoint).where(
                or_(KnowledgePoint.title.ilike(like), KnowledgePoint.summary.ilike(like))
            ).limit(10)
        )
    ).scalars().all()
    ex_query = select(Exercise).where(or_(Exercise.title.ilike(like), Exercise.content_md.ilike(like)))
    total = (await db.execute(select(func.count()).select_from(ex_query.subquery()))).scalar_one()
    ex_rows = (
        await db.execute(ex_query.offset((page - 1) * size).limit(size))
    ).scalars().all()
    items = [
        *[{"kind": "kp", "id": k.id, "title": k.title, "chapter_id": k.chapter_id} for k in kp_rows],
        *[{"kind": "exercise", "id": e.id, "title": e.title, "chapter_id": e.chapter_id,
           "type": e.type.value, "difficulty": e.difficulty.value} for e in ex_rows],
    ]
    return ok(page_data(items, total, page, size))
