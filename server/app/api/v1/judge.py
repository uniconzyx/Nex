from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.queue import get_arq
from app.core.rate_limit import check_daily_quota, check_rate_limit
from app.core.responses import AppError, NOT_FOUND, ok
from app.db import get_db
from app.models.enums import Plan, SubmissionStatus
from app.models.exercise import Exercise
from app.models.submission import Submission
from app.models.user import User, UserProfile
from app.schemas.judge import SubmissionIn
from app.services import judge0

router = APIRouter(tags=["judge"])


def _quota_for(plan: Plan) -> int:
    return settings.judge_daily_quota_pro if plan == Plan.pro else settings.judge_daily_quota_free


@router.post("/judge/submissions", status_code=202)
async def create_submission(
    body: SubmissionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(f"judge:{user.id}", 30, 60)  # 每分钟最多 30 次
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    plan = profile.plan if profile else Plan.free
    quota_left = await check_daily_quota(user.id, "judge", _quota_for(plan))

    cases: list[tuple[str, str]] = []
    time_limit_s = 2.0
    mem_kb = 256 * 1024
    if body.exercise_id is not None:
        exercise = await db.get(Exercise, body.exercise_id)
        if exercise is None:
            raise AppError(NOT_FOUND, "题目不存在", http_status=404)
        cases = [(tc.input, tc.expected_output) for tc in exercise.test_cases] or [("", "")]
        time_limit_s = exercise.time_limit_ms / 1000
        mem_kb = exercise.memory_limit_mb * 1024
    else:
        cases = [(body.stdin or "", "")]  # 自由运行台：无期望输出

    sub = Submission(
        user_id=user.id, exercise_id=body.exercise_id, lang=body.lang,
        source_code=body.source_code, stdin=body.stdin, status=SubmissionStatus.queued,
        total=len(cases),
    )
    db.add(sub)
    await db.flush()

    tokens = await judge0.submit_batch(
        body.source_code, body.lang, cases, time_limit_s, mem_kb
    )
    sub.judge0_token = ",".join(tokens)
    sub.status = SubmissionStatus.running
    await db.commit()

    arq = await get_arq()
    await arq.enqueue_job("poll_judge", sub.id)
    return ok({"submission_id": sub.id, "status": sub.status.value,
               "poll_after_ms": 800, "quota_left": quota_left}, "已提交")


@router.get("/judge/submissions/{submission_id}")
async def get_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await db.get(Submission, submission_id)
    if sub is None or sub.user_id != user.id:
        raise AppError(NOT_FOUND, "提交记录不存在", http_status=404)
    data = {
        "id": sub.id, "status": sub.status.value, "passed": sub.passed, "total": sub.total,
        "time_ms": sub.time_ms, "memory_kb": sub.memory_kb,
        "diagnosis_md": sub.diagnosis_md, "lang": sub.lang.value,
    }
    if sub.status not in (SubmissionStatus.queued, SubmissionStatus.running):
        data["stdout"] = sub.stdout
        data["stderr"] = sub.stderr
    return ok(data)


@router.get("/judge/submissions")
async def submission_history(
    exercise_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [Submission.user_id == user.id]
    if exercise_id:
        conds.append(Submission.exercise_id == exercise_id)
    rows = (
        await db.execute(
            select(Submission).where(*conds)
            .order_by(Submission.created_at.desc())
            .offset((page - 1) * size).limit(size)
        )
    ).scalars().all()
    return ok([
        {"id": s.id, "exercise_id": s.exercise_id, "lang": s.lang.value,
         "status": s.status.value, "time_ms": s.time_ms, "created_at": s.created_at.isoformat()}
        for s in rows
    ])
