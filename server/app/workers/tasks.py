from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import SessionLocal
from app.models.enums import QuestionType, SubmissionStatus, SyncStatus
from app.models.exercise import Exercise, TestCase
from app.models.progress import WrongQuestion
from app.models.resource import SyncJob
from app.models.submission import Submission
from app.services import judge0
from app.services.diagnosis import diagnose

_POLL_MAX = 20  # 最多轮询 20 次 × 1.5s ≈ 30s 封顶


async def poll_judge(ctx: dict, submission_id: int) -> None:
    """轮询 Judge0 直至终态：比对用例 → 落库 → 错题收录 → 规则库诊断 → AI 兜底。"""
    async with SessionLocal() as db:
        sub = await db.get(Submission, submission_id)
        if sub is None or not sub.judge0_token:
            return
        tokens = sub.judge0_token.split(",")

    for _ in range(_POLL_MAX):
        results = await judge0.fetch_results(tokens)
        if judge0.is_finished(results):
            break
        await __import__("asyncio").sleep(1.5)
    else:
        async with SessionLocal() as db:
            sub = await db.get(Submission, submission_id)
            if sub:
                sub.status = SubmissionStatus.ie
                sub.stderr = "判题超时（系统内部）"
                await db.commit()
        return

    async with SessionLocal() as db:
        sub = await db.get(Submission, submission_id)
        if sub is None:
            return
        await _finalize(db, sub, results)


async def _finalize(db: AsyncSession, sub: Submission, results: list[dict]) -> None:
    # 汇总状态：任一用例非 AC 即取最严重（CE > RE > TLE > MLE > WA）
    severity = [
        SubmissionStatus.ce, SubmissionStatus.re, SubmissionStatus.tle,
        SubmissionStatus.mle, SubmissionStatus.wa, SubmissionStatus.ac,
    ]
    statuses = {judge0.STATUS_MAP.get(r["status"]["id"], SubmissionStatus.ie) for r in results}
    final = next((s for s in severity if s in statuses), SubmissionStatus.ie)

    passed = sum(1 for r in results if r["status"]["id"] == 3)
    sub.status = final
    sub.passed = passed
    sub.total = len(results)

    first_bad = next((r for r in results if r["status"]["id"] != 3), results[0])
    sub.stdout = judge0.truncate(first_bad.get("stdout"))
    raw_err = first_bad.get("compile_output") or first_bad.get("stderr")
    sub.stderr = judge0.truncate(raw_err)
    times = [float(r["time"]) for r in results if r.get("time")]
    mems = [int(r["memory"]) for r in results if r.get("memory")]
    sub.time_ms = int(max(times) * 1000) if times else None
    sub.memory_kb = max(mems) if mems else None

    # 规则库诊断；未命中则入队 AI 兜底
    if final in (SubmissionStatus.ce, SubmissionStatus.re, SubmissionStatus.wa):
        sub.diagnosis_md = diagnose(sub.stderr, final.value)
        if sub.diagnosis_md is None and sub.stderr:
            from arq.connections import create_pool
            from app.workers.settings import redis_settings

            pool = await create_pool(redis_settings)
            await pool.enqueue_job("ai_diagnose", sub.id)

    # 错题自动收录（仅绑定题目的提交）
    if sub.exercise_id and final != SubmissionStatus.ac:
        existing = (
            await db.execute(
                select(WrongQuestion).where(
                    WrongQuestion.user_id == sub.user_id,
                    WrongQuestion.question_type == QuestionType.exercise,
                    WrongQuestion.question_id == sub.exercise_id,
                )
            )
        ).scalar_one_or_none()
        next_review = datetime.now(UTC) + timedelta(days=1)
        if existing is None:
            db.add(WrongQuestion(
                user_id=sub.user_id, question_type=QuestionType.exercise,
                question_id=sub.exercise_id, wrong_count=1, last_result="wrong",
                next_review_at=next_review,
            ))
        else:
            existing.wrong_count += 1
            existing.last_result = "wrong"
            existing.next_review_at = next_review
    await db.commit()


async def run_sync(ctx: dict, source: str, mode: str, job_id: int) -> None:
    """资源同步任务入口（手动触发或 cron）。"""
    async with SessionLocal() as db:
        job = await db.get(SyncJob, job_id)
        if job is None:
            return
        job.started_at = datetime.now(UTC)
        await db.commit()
        try:
            if source == "github":
                from app.services.sync.github_sync import sync_github

                stats = await sync_github(db, mode)
            elif source == "leetcode":
                from app.services.sync.leetcode_sync import sync_leetcode

                stats = await sync_leetcode(db, mode)
            else:
                raise ValueError(f"不支持的同步源: {source}")
            job.status = SyncStatus.success
            job.stats = stats
        except Exception as exc:  # noqa: BLE001
            job.status = SyncStatus.failed
            job.error = str(exc)[:2000]
        job.finished_at = datetime.now(UTC)
        await db.commit()


async def daily_sync_cron(ctx: dict) -> None:
    """每日全量同步（架构文档 9.2：03:00）。"""
    from arq.connections import create_pool
    from app.workers.settings import redis_settings

    pool = await create_pool(redis_settings)
    async with SessionLocal() as db:
        for source in ("github", "leetcode"):
            job = SyncJob(source=source, mode="full")
            db.add(job)
            await db.flush()
            await pool.enqueue_job("run_sync", source, "full", job.id)
        await db.commit()


async def ai_diagnose(ctx: dict, submission_id: int) -> None:
    """规则库未命中时的 AI 诊断兜底。AI 不可用时静默放弃（不影响判题主流程）。"""
    from app.models.enums import AIMode
    from app.services.ai_provider import build_messages, get_provider, pick_model

    async with SessionLocal() as db:
        sub = await db.get(Submission, submission_id)
        if sub is None or sub.diagnosis_md:
            return
        try:
            provider = get_provider()
        except Exception:
            return
        context = {"code": sub.source_code, "chapter": ""}
        messages = build_messages(
            AIMode.diagnose.value,
            [{"role": "user", "content": f"编译/运行出错，stderr：\n```\n{(sub.stderr or '')[:3000]}\n```"}],
            context,
        )
        chunks: list[str] = []
        try:
            async for chunk in provider.stream(messages, pick_model(AIMode.diagnose.value)):
                chunks.append(chunk)
        except Exception:
            return
        if chunks:
            sub.diagnosis_md = "**AI 诊断（CppCat）**\n\n" + "".join(chunks)
            await db.commit()
