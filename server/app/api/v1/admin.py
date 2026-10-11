from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.queue import get_arq
from app.core.responses import AppError, NOT_FOUND, PARAM_ERROR, ok
from app.db import get_db
from app.models.content import Chapter, Lesson
from app.models.enums import LessonType
from app.models.exercise import Exercise, InterviewQuestion
from app.models.project import Project
from app.models.resource import SyncJob
from app.models.user import User
from app.schemas.resource import SyncTriggerIn

router = APIRouter(prefix="/admin", tags=["admin"])

# 7 类内容的最低数量要求（PRD 第 9 节）
REQUIRED = {"concepts": 1, "pitfalls": 1, "examples": 10, "exercises": 5,
            "interview_questions": 3, "projects": 1}


@router.post("/sync")
async def trigger_sync(
    body: SyncTriggerIn,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.source not in ("github", "leetcode"):
        raise AppError(PARAM_ERROR, "source 仅支持 github / leetcode（nowcoder 走离线导入）")
    job = SyncJob(source=body.source, mode=body.mode)
    db.add(job)
    await db.flush()
    await db.commit()
    arq = await get_arq()
    await arq.enqueue_job("run_sync", body.source, body.mode, job.id)
    return ok({"job_id": job.id, "status": "running"})


@router.get("/sync/jobs")
async def sync_jobs(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(20))
    ).scalars().all()
    return ok([
        {"id": j.id, "source": j.source.value, "mode": j.mode.value, "status": j.status.value,
         "stats": j.stats, "error": j.error,
         "started_at": j.started_at.isoformat() if j.started_at else None,
         "finished_at": j.finished_at.isoformat() if j.finished_at else None}
        for j in rows
    ])


@router.get("/sync/jobs/{job_id}")
async def sync_job_detail(
    job_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(SyncJob, job_id)
    if job is None:
        raise AppError(NOT_FOUND, "任务不存在", http_status=404)
    return ok({"id": job.id, "source": job.source.value, "status": job.status.value,
               "stats": job.stats, "error": job.error})


@router.post("/content/import")
async def import_bank(
    file: UploadFile,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """题库 JSON 导入：schema 全量校验 → 整包事务，失败回滚。"""
    from app.services.sync.importer import import_package

    raw = await file.read()
    try:
        result = await import_package(db, raw.decode("utf-8"))
    except ValueError as exc:
        raise AppError(PARAM_ERROR, f"题库包校验失败：{exc}")
    return ok(result, "导入成功")


@router.get("/content/coverage")
async def content_coverage(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """20 章 × 7 类内容完整性报告（与 CI 校验脚本同口径）。"""
    chapters = (
        await db.execute(
            select(Chapter).where(Chapter.deleted_at.is_(None)).order_by(Chapter.course_id, Chapter.idx)
        )
    ).scalars().all()

    async def lesson_count(chapter_id: int, ltype: LessonType) -> int:
        return (await db.execute(
            select(func.count()).select_from(Lesson)
            .where(Lesson.chapter_id == chapter_id, Lesson.type == ltype,
                   Lesson.deleted_at.is_(None))
        )).scalar_one()

    report = []
    for ch in chapters:
        counts = {
            "concepts": await lesson_count(ch.id, LessonType.concept),
            "pitfalls": await lesson_count(ch.id, LessonType.pitfall),
            "examples": await lesson_count(ch.id, LessonType.example),
            "exercises": (await db.execute(
                select(func.count()).select_from(Exercise).where(Exercise.chapter_id == ch.id)
            )).scalar_one(),
            "interview_questions": (await db.execute(
                select(func.count()).select_from(InterviewQuestion)
                .where(InterviewQuestion.chapter_id == ch.id)
            )).scalar_one(),
            "projects": (await db.execute(
                select(func.count()).select_from(Project)
                .where(Project.chapter_id == ch.id, Project.deleted_at.is_(None))
            )).scalar_one(),
        }
        gaps = [k for k, need in REQUIRED.items() if counts[k] < need]
        if not ch.goals:
            gaps.append("goals")
        report.append({
            "code": ch.code, "title": ch.title, "counts": counts,
            "has_goals": bool(ch.goals), "complete": not gaps, "gaps": gaps,
        })
    done = sum(1 for r in report if r["complete"])
    return ok({"chapters": report, "complete": done, "total": len(report)})
