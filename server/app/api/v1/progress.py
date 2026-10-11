from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.responses import AppError, NOT_FOUND, ok
from app.db import get_db
from app.models.content import Chapter, KnowledgePoint
from app.models.enums import (
    Direction,
    PlanGenerator,
    PlanStatus,
    QuestionType,
    TaskStatus,
    TaskTarget,
)
from app.models.progress import (
    Achievement,
    DailyTask,
    Note,
    Progress,
    StudyPlan,
    UserAchievement,
    WrongQuestion,
)
from app.models.submission import Submission
from app.models.user import User
from app.schemas.ai import PlanGenerateIn
from app.schemas.content import FavoriteIn, NoteIn
from app.schemas.judge import RedoIn
from app.models.resource import Favorite

router = APIRouter(tags=["progress"])


@router.get("/progress/dashboard")
async def dashboard(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    mastery = (
        await db.execute(
            select(KnowledgePoint.chapter_id, func.avg(Progress.mastery), func.count())
            .join(Progress, Progress.kp_id == KnowledgePoint.id)
            .where(Progress.user_id == user.id)
            .group_by(KnowledgePoint.chapter_id)
        )
    ).all()
    submission_count = (
        await db.execute(select(func.count()).select_from(Submission).where(Submission.user_id == user.id))
    ).scalar_one()
    ac_count = (
        await db.execute(
            select(func.count()).select_from(Submission)
            .where(Submission.user_id == user.id, Submission.status == "ac")
        )
    ).scalar_one()
    wrong_open = (
        await db.execute(
            select(func.count()).select_from(WrongQuestion)
            .where(WrongQuestion.user_id == user.id, WrongQuestion.last_result == "wrong")
        )
    ).scalar_one()
    today_tasks = (
        await db.execute(
            select(DailyTask).join(StudyPlan, StudyPlan.id == DailyTask.plan_id)
            .where(StudyPlan.user_id == user.id, DailyTask.date == date.today())
        )
    ).scalars().all()
    return ok({
        "chapter_mastery": [
            {"chapter_id": cid, "mastery_avg": round(float(avg), 2), "kp_count": cnt}
            for cid, avg, cnt in mastery
        ],
        "submissions": submission_count,
        "ac_count": ac_count,
        "wrong_open": wrong_open,
        "today_tasks": [
            {"id": t.id, "title": t.title, "status": t.status.value,
             "target_type": t.target_type.value, "target_id": t.target_id}
            for t in today_tasks
        ],
    })


@router.get("/wrong-questions")
async def wrong_questions(
    mode: str = Query("all", pattern="^(all|review)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [WrongQuestion.user_id == user.id]
    if mode == "review":
        conds += [
            WrongQuestion.last_result == "wrong",
            WrongQuestion.next_review_at <= datetime.now(UTC),
        ]
    rows = (
        await db.execute(select(WrongQuestion).where(*conds).order_by(WrongQuestion.updated_at.desc()))
    ).scalars().all()
    return ok([
        {"id": w.id, "question_type": w.question_type.value, "question_id": w.question_id,
         "wrong_count": w.wrong_count, "right_count": w.right_count,
         "next_review_at": w.next_review_at.isoformat() if w.next_review_at else None}
        for w in rows
    ])


@router.post("/wrong-questions/{wq_id}/redo")
async def redo_wrong(
    wq_id: int,
    body: RedoIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    w = await db.get(WrongQuestion, wq_id)
    if w is None or w.user_id != user.id:
        raise AppError(NOT_FOUND, "错题记录不存在", http_status=404)
    now = datetime.now(UTC)
    if body.result == "right":
        w.right_count += 1
        w.last_result = "right" if w.right_count >= 2 else "wrong"
        # 间隔复习：1d → 3d → 7d
        step = min(w.right_count, 3)
        w.next_review_at = now + timedelta(days=[1, 3, 7, 7][step])
    else:
        w.wrong_count += 1
        w.right_count = 0
        w.last_result = "wrong"
        w.next_review_at = now + timedelta(days=1)
    await db.commit()
    return ok(message="已记录")


@router.post("/plans/generate")
async def generate_plan(
    body: PlanGenerateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成学习计划骨架：按章节顺序均分到周（AI 润色在阶段 6 接入 plan 模式）。"""
    direction = Direction(body.direction)
    chapters = (
        await db.execute(
            select(Chapter).join_from(Chapter, Chapter.course)
            .where(Chapter.deleted_at.is_(None)).order_by(Chapter.idx)
        )
    ).scalars().all()
    if not chapters:
        raise AppError(NOT_FOUND, "课程内容尚未初始化", http_status=404)

    start = date.today()
    plan = StudyPlan(
        user_id=user.id, direction=direction, start_date=start,
        end_date=start + timedelta(weeks=body.weeks),
        weekly_hours=body.weekly_hours, generated_by=PlanGenerator.ai,
        config={"weeks": body.weeks},
    )
    db.add(plan)
    await db.flush()

    per_day = max(1, len(chapters) // (body.weeks * 7) + 1)
    idx = 0
    for offset in range(body.weeks * 7):
        for _ in range(per_day):
            if idx >= len(chapters):
                break
            ch = chapters[idx]
            db.add(DailyTask(
                plan_id=plan.id, date=start + timedelta(days=offset),
                target_type=TaskTarget.kp, target_id=ch.id,
                title=f"学习章节：{ch.title}",
            ))
            idx += 1
    await db.commit()
    return ok({"plan_id": plan.id, "start_date": start.isoformat(),
               "end_date": plan.end_date.isoformat()}, "计划已生成")


@router.get("/plans/current")
async def current_plan(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = (
        await db.execute(
            select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.status == PlanStatus.active)
            .order_by(StudyPlan.created_at.desc())
        )
    ).scalars().first()
    if plan is None:
        return ok(None, "暂无进行中的学习计划")
    tasks = (
        await db.execute(
            select(DailyTask).where(DailyTask.plan_id == plan.id, DailyTask.date == date.today())
        )
    ).scalars().all()
    return ok({
        "plan_id": plan.id, "direction": plan.direction.value,
        "start_date": plan.start_date.isoformat(), "end_date": plan.end_date.isoformat(),
        "today_tasks": [{"id": t.id, "title": t.title, "status": t.status.value} for t in tasks],
    })


@router.post("/daily-tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(DailyTask, task_id)
    if task is None:
        raise AppError(NOT_FOUND, "任务不存在", http_status=404)
    plan = await db.get(StudyPlan, task.plan_id)
    if plan is None or plan.user_id != user.id:
        raise AppError(NOT_FOUND, "任务不存在", http_status=404)
    task.status = TaskStatus.done
    task.done_at = datetime.now(UTC)
    await db.commit()
    return ok(message="已完成")


@router.get("/achievements/my")
async def my_achievements(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Achievement, UserAchievement.unlocked_at)
            .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
            .where(UserAchievement.user_id == user.id)
        )
    ).all()
    return ok([
        {"code": a.code, "title": a.title, "description": a.description,
         "icon": a.icon, "unlocked_at": ua.isoformat() if ua else None}
        for a, ua in rows
    ])


@router.post("/notes")
async def create_note(
    body: NoteIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = Note(user_id=user.id, target_type=body.target_type,
                target_id=body.target_id, content_md=body.content_md)
    db.add(note)
    await db.commit()
    return ok({"note_id": note.id}, "已保存")


@router.get("/notes")
async def list_notes(
    target_type: str,
    target_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Note).where(Note.user_id == user.id, Note.target_type == target_type,
                               Note.target_id == target_id)
        )
    ).scalars().all()
    return ok([{"id": n.id, "content_md": n.content_md, "updated_at": n.updated_at.isoformat()} for n in rows])


@router.post("/favorites")
async def add_favorite(
    body: FavoriteIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fav = Favorite(user_id=user.id, target_type=body.target_type, target_id=body.target_id)
    db.add(fav)
    await db.commit()
    return ok(message="已收藏")


@router.delete("/favorites")
async def remove_favorite(
    body: FavoriteIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fav = (
        await db.execute(
            select(Favorite).where(Favorite.user_id == user.id,
                                   Favorite.target_type == body.target_type,
                                   Favorite.target_id == body.target_id)
        )
    ).scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
    return ok(message="已取消收藏")
