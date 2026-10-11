import json
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import check_daily_quota
from app.core.responses import AppError, NOT_FOUND, ok
from app.db import get_db
from app.models.ai import AIConversation, AIMessage
from app.models.enums import AIMode, MessageRole, Plan
from app.models.exercise import Exercise
from app.models.progress import Progress, WrongQuestion
from app.models.user import User, UserProfile
from app.schemas.ai import (
    ChatIn,
    ConversationIn,
    InsightOut,
    MessageIn,
    PlanGenerateIn,
    QuizIn,
    QuizOut,
    QuizQuestionOut,
)
from app.services.ai_provider import build_messages, get_provider, pick_model
from app.services.insight import analyze_weakness
from app.services.quiz import generate_quiz
from app.services.retrieval import (
    KnowledgeIndex,
    build_corpus_from_content,
    build_corpus_from_exercises,
)

router = APIRouter(tags=["ai"])

_CONTENT_DIR = Path(settings.content_dir)


def _ai_quota(plan: Plan) -> int:
    return settings.ai_daily_quota_pro if plan == Plan.pro else settings.ai_daily_quota_free


async def _remaining_quota(db: AsyncSession, user_id: int) -> int:
    from datetime import UTC, datetime

    from app.core.redis_client import get_redis

    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one_or_none()
    limit = _ai_quota(profile.plan if profile else Plan.free)
    r = get_redis()
    today = datetime.now(UTC).strftime("%Y%m%d")
    used = int(await r.get(f"quota:ai:{user_id}:{today}") or 0)
    return max(limit - used, 0)


async def _exercise_rows(db: AsyncSession) -> list[dict]:
    """轻量投影：仅取检索/测验所需的字段，避免加载用例大字段。"""

    def _source_label(src: str) -> str:
        return {"self": "cppmind", "leetcode": "leetcode", "nowcoder": "nowcoder"}.get(src, "cppmind")

    rows = (
        await db.execute(
            select(
                Exercise.id,
                Exercise.chapter_id,
                Exercise.type,
                Exercise.difficulty,
                Exercise.title,
                Exercise.content_md,
                Exercise.explanation,
                Exercise.source,
                Exercise.external_url,
                Exercise.external_id,
            )
        )
    ).all()
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "chapter_id": r.chapter_id,
                "type": r.type.value if hasattr(r.type, "value") else r.type,
                "difficulty": r.difficulty.value if hasattr(r.difficulty, "value") else r.difficulty,
                "title": r.title,
                "content_md": r.content_md or "",
                "explanation": r.explanation or "",
                "source": _source_label(r.source.value if hasattr(r.source, "value") else r.source),
                "external_url": r.external_url,
                "external_id": r.external_id,
                "subject": "",
            }
        )
    return out


async def _wrong_rows(db: AsyncSession, user_id: int) -> list[dict]:
    rows = (
        await db.execute(
            select(
                WrongQuestion.chapter_id,
                WrongQuestion.question_type,
                WrongQuestion.question_id,
                WrongQuestion.wrong_count,
                WrongQuestion.right_count,
            ).where(WrongQuestion.user_id == user_id)
        )
    ).all()
    return [
        {
            "chapter_id": r.chapter_id,
            "question_type": r.question_type.value if hasattr(r.question_type, "value") else r.question_type,
            "question_id": r.question_id,
            "wrong_count": r.wrong_count,
            "right_count": r.right_count,
        }
        for r in rows
    ]


async def _build_index(db: AsyncSession) -> KnowledgeIndex:
    lesson_docs = build_corpus_from_content(_CONTENT_DIR)
    exercise_docs = build_corpus_from_exercises(await _exercise_rows(db))
    return KnowledgeIndex(lesson_docs + exercise_docs)


# ---------------------------------------------------------------------------
# 既有会话端点（阶段 5）
# ---------------------------------------------------------------------------

@router.post("/ai/conversations")
async def create_conversation(
    body: ConversationIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = AIConversation(
        user_id=user.id, mode=AIMode(body.mode), chapter_id=body.chapter_id, title=body.title
    )
    db.add(conv)
    await db.commit()
    return ok({"conversation_id": conv.id})


@router.get("/ai/conversations")
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(AIConversation).where(AIConversation.user_id == user.id)
            .order_by(AIConversation.updated_at.desc()).limit(50)
        )
    ).scalars().all()
    return ok([
        {"id": c.id, "mode": c.mode.value, "title": c.title, "chapter_id": c.chapter_id,
         "updated_at": c.updated_at.isoformat()}
        for c in rows
    ])


@router.get("/ai/conversations/{conv_id}")
async def conversation_history(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(AIConversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise AppError(NOT_FOUND, "会话不存在", http_status=404)
    return ok({
        "id": conv.id, "mode": conv.mode.value, "title": conv.title,
        "messages": [
            {"role": m.role.value, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in conv.messages
        ],
    })


@router.post("/ai/conversations/{conv_id}/messages")
async def send_message(
    conv_id: int,
    body: MessageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await db.get(AIConversation, conv_id)
    if conv is None or conv.user_id != user.id:
        raise AppError(NOT_FOUND, "会话不存在", http_status=404)

    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    quota_left = await check_daily_quota(
        user.id, "ai", _ai_quota(profile.plan if profile else Plan.free)
    )

    db.add(AIMessage(conversation_id=conv.id, role=MessageRole.user, content=body.content))
    await db.flush()

    history = [{"role": m.role.value, "content": m.content} for m in conv.messages[-20:]]
    context = dict(conv.context_snapshot or {})
    if body.attach:
        context.update(body.attach)
        conv.context_snapshot = context

    index = await _build_index(db)
    retrieved = index.retrieve(body.content, k=4, chapter_id=conv.chapter_id)
    messages = build_messages(conv.mode.value, history, context, retrieved=retrieved)
    model = pick_model(conv.mode.value)
    provider = get_provider()

    async def event_stream():
        chunks: list[str] = []
        yield f'event: meta\ndata: {{"model": "{model}", "mode": "{conv.mode.value}", "conversation_id": {conv.id}}}\n\n'
        try:
            async for chunk in provider.stream(messages, model):
                chunks.append(chunk)
                yield f"event: delta\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"event: error\ndata: {json.dumps({'message': str(exc)[:200]}, ensure_ascii=False)}\n\n"
        finally:
            if chunks:
                db.add(AIMessage(
                    conversation_id=conv.id, role=MessageRole.assistant,
                    content="".join(chunks), model=model,
                    tokens_in=sum(len(m["content"]) for m in messages) // 4,
                    tokens_out=sum(len(c) for c in chunks) // 4,
                ))
                await db.commit()
            yield f'event: done\ndata: {{"quota_left": {quota_left}}}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/ai/quota")
async def ai_quota(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok({"remaining": await _remaining_quota(db, user.id)})


# ---------------------------------------------------------------------------
# Phase 6：统一对话入口 / 自适应测验 / 薄弱点诊断 / 学习计划
# ---------------------------------------------------------------------------

@router.post("/ai/chat")
async def chat(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """与 Flutter /ai/chat 契约对齐：单条消息 + history，自动建/续会话，SSE 流式。

    Phase 6 改动：注入课程检索锚定（retrieved），让 CppCat 回答基于真实资料。
    """
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    quota_left = await check_daily_quota(
        user.id, "ai", _ai_quota(profile.plan if profile else Plan.free)
    )

    if body.conversation_id:
        conv = await db.get(AIConversation, body.conversation_id)
        if conv is None or conv.user_id != user.id:
            raise AppError(NOT_FOUND, "会话不存在", http_status=404)
    else:
        conv = AIConversation(
            user_id=user.id,
            mode=AIMode(body.mode),
            chapter_id=body.chapter_id,
            title=body.message[:50],
        )
        db.add(conv)
        await db.flush()

    db.add(AIMessage(conversation_id=conv.id, role=MessageRole.user, content=body.message))
    await db.flush()

    history = [{"role": m["role"], "content": m["content"]} for m in body.history if m.get("content")]
    context: dict = {}
    if body.attach:
        context.update(body.attach)

    index = await _build_index(db)
    retrieved = index.retrieve(body.message, k=4, chapter_id=body.chapter_id)
    messages = build_messages(body.mode, history, context, retrieved=retrieved)
    model = pick_model(body.mode)
    provider = get_provider()

    async def event_stream():
        chunks: list[str] = []
        yield f'event: meta\ndata: {{"model": "{model}", "mode": "{body.mode}", "conversation_id": {conv.id}}}\n\n'
        try:
            async for chunk in provider.stream(messages, model):
                chunks.append(chunk)
                yield f"event: delta\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"event: error\ndata: {json.dumps({'message': str(exc)[:200]}, ensure_ascii=False)}\n\n"
        finally:
            if chunks:
                db.add(AIMessage(
                    conversation_id=conv.id, role=MessageRole.assistant,
                    content="".join(chunks), model=model,
                    tokens_in=sum(len(m["content"]) for m in messages) // 4,
                    tokens_out=sum(len(c) for c in chunks) // 4,
                ))
                await db.commit()
            yield f'event: done\ndata: {{"quota_left": {quota_left}, "conversation_id": {conv.id}}}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/ai/generate-quiz")
async def generate_quiz_endpoint(
    body: QuizIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """基于用户薄弱点（错题本）从真实题库抽题；无薄弱点时按难度均衡抽样。"""
    wrong = await _wrong_rows(db, user.id)

    weak_chapters: list[int] | None = None
    weak_types: list[str] | None = None
    based_on_weak = bool(wrong)

    if body.chapter_ids:
        weak_chapters = body.chapter_ids
        based_on_weak = True
    elif wrong:
        weak_chapters = sorted({w["chapter_id"] for w in wrong if w["chapter_id"] is not None})

    if body.types:
        weak_types = body.types
        based_on_weak = True
    elif wrong:
        weak_types = sorted({w["question_type"] for w in wrong})

    exercises = await _exercise_rows(db)
    questions = generate_quiz(
        exercises=exercises,
        weak_chapters=weak_chapters,
        weak_types=weak_types,
        n=body.n,
    )
    return ok(QuizOut(
        questions=[QuizQuestionOut(**q.__dict__) for q in questions],
        based_on_weak=based_on_weak,
    ).model_dump())


@router.get("/ai/insight")
async def insight(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """薄弱点诊断：聚合错题本 + 进度，给出弱章节排名与学习建议。"""
    wrong = await _wrong_rows(db, user.id)
    progress_rows = (
        await db.execute(
            select(Progress.kp_id, Progress.chapter_id, Progress.mastery).where(Progress.user_id == user.id)
        )
    ).all()
    progress = [
        {"kp_id": p.kp_id, "chapter_id": p.chapter_id, "mastery": p.mastery} for p in progress_rows
    ]
    result = analyze_weakness(error_book=wrong, progress=progress)
    return ok(InsightOut(
        weak_chapters=[c.__dict__ for c in result.weak_chapters],
        weak_types=result.weak_types,
        recommendations=result.recommendations,
        total_wrong=result.total_wrong,
    ).model_dump())


@router.post("/ai/plan")
async def plan(
    body: PlanGenerateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """学习计划：注入用户进度 + 薄弱点，流式生成按周分解计划（架构 §8.3）。"""
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    quota_left = await check_daily_quota(
        user.id, "ai", _ai_quota(profile.plan if profile else Plan.free)
    )

    wrong = await _wrong_rows(db, user.id)
    progress_rows = (
        await db.execute(
            select(Progress.chapter_id, Progress.mastery).where(Progress.user_id == user.id)
        )
    ).all()
    progress = [{"chapter_id": p.chapter_id, "mastery": p.mastery} for p in progress_rows]
    analysis = analyze_weakness(error_book=wrong, progress=progress)

    context = {
        "progress": (
            f"方向={body.direction}，每周{body.weekly_hours}小时，共{body.weeks}周；"
            f"已完成章节掌握度记录 {len(progress)} 条；"
            f"薄弱章节：{', '.join(str(c.chapter_id) for c in analysis.weak_chapters[:5]) or '无'}"
        ),
        "wrong_questions": (
            f"累计错误 {analysis.total_wrong} 次，最弱题型："
            f"{analysis.weak_types[0]['label'] if analysis.weak_types else '无'}"
        ),
    }
    history: list[dict] = []
    index = await _build_index(db)
    query = f"{body.direction} 学习计划 薄弱章节 {[c.chapter_id for c in analysis.weak_chapters[:3]]}"
    retrieved = index.retrieve(query, k=3)
    messages = build_messages("plan", history, context, retrieved=retrieved)
    model = pick_model("plan")
    provider = get_provider()

    async def event_stream():
        chunks: list[str] = []
        yield f'event: meta\ndata: {{"model": "{model}", "mode": "plan"}}\n\n'
        try:
            async for chunk in provider.stream(messages, model):
                chunks.append(chunk)
                yield f"event: delta\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"event: error\ndata: {json.dumps({'message': str(exc)[:200]}, ensure_ascii=False)}\n\n"
        finally:
            yield f'event: done\ndata: {{"quota_left": {quota_left}}}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")  # noqa: RET505
