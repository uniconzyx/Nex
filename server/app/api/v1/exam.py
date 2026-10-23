"""考研题库 API（框架 / 知识点 / 分类总结 / 题库 / 套卷 / 精读 / 判分）。

契约见 docs/API-Exam.md。这里只做三件事：取参数、调用 services.exam_bank、
用 ok() 包一层。任何业务判断都不写进路由，路由里出现 if 就说明分层错了。

三个刻意的取舍：
  - 列表一律分页（page/size），即使当前只有 5 条——客户端不必为「以后变多」改代码；
  - 题库列表不返回答案与讲解（answer/explain/walkthrough），否则「刷题」变成「看答案」；
  - 判分是无状态 POST：不写库、不落进度，因此天然可重试，不需要幂等键。
"""
from typing import Literal

from fastapi import APIRouter, Query

from app.core.responses import ok
from app.schemas.exam import GradeIn
from app.services import exam_bank

router = APIRouter(tags=["exam"])


@router.get("/exams")
async def list_exams():
    """考试目录。固定 6 项，属于枚举型资源，故不分页。"""
    return ok(exam_bank.catalog())


@router.get("/exams/{exam}")
async def exam_detail(exam: str):
    return ok(exam_bank.exam_detail(exam))


@router.get("/exams/{exam}/subjects/{subject}/frameworks")
async def subject_frameworks(exam: str, subject: str):
    """解题框架：专题 → 题型 → 固定步骤 + 陷阱。"""
    return ok(exam_bank.framework(exam, subject))


@router.get("/exams/{exam}/subjects/{subject}/knowledge")
async def subject_knowledge(exam: str, subject: str):
    return ok(exam_bank.knowledge(exam, subject))


@router.get("/exams/{exam}/subjects/{subject}/summaries")
async def subject_summaries(exam: str, subject: str):
    """分类总结：认题信号 + 固定步骤 + 技巧 + 陷阱 + 本专题题目清单。"""
    return ok(exam_bank.summaries(exam, subject))


@router.get("/exams/{exam}/subjects/{subject}/questions")
async def subject_questions(
    exam: str,
    subject: str,
    topic: str | None = Query(None, description="专题 id，取值见 frameworks"),
    qtype: str | None = Query(None, alias="type", description="题型：choice/multi/blank/calc/design"),
    difficulty: int | None = Query(None, ge=1, le=5),
    q: str | None = Query(None, max_length=100, description="题干关键词"),
    sort: Literal["order", "difficulty"] = Query("order"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=exam_bank.MAX_PAGE_SIZE),
):
    """题目列表：只给题干与元信息，不给答案。"""
    return ok(exam_bank.list_questions(
        exam, subject,
        topic=topic, qtype=qtype, difficulty=difficulty, keyword=q,
        sort=sort, page=page, size=size,
    ))


@router.get("/exams/{exam}/subjects/{subject}/questions/{question_id}")
async def question_detail(exam: str, subject: str, question_id: str):
    """单题详情：四层讲解按 framework → approach → points → solution 返回。"""
    return ok(exam_bank.question_detail(exam, subject, question_id))


@router.get("/exams/{exam}/subjects/{subject}/reading")
async def subject_reading(exam: str, subject: str):
    """精读篇目索引。没有精读材料的科目返回空列表，而不是 404——
    集合存在但为空，和「资源不存在」是两件事。"""
    return ok(exam_bank.reading_index(exam, subject))


@router.get("/exams/{exam}/subjects/{subject}/reading/{passage_id}")
async def reading_passage(exam: str, subject: str, passage_id: str):
    """篇目详情：段落主旨、词伙、长难句拆解、题目定位、读后复盘。"""
    return ok(exam_bank.reading_passage(exam, subject, passage_id))


@router.get("/exams/{exam}/papers")
async def list_papers(
    exam: str,
    subject: str | None = Query(None, description="按卷面覆盖科目筛选；整卷会出现在其覆盖的每个科目下"),
    kind: str | None = Query(None, description="卷型，如 mock"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=exam_bank.MAX_PAGE_SIZE),
):
    return ok(exam_bank.list_papers(exam, subject=subject, kind=kind, page=page, size=size))


@router.get("/exams/{exam}/papers/{paper_id}")
async def paper_detail(exam: str, paper_id: str):
    """套卷详情：分区 → 题目。题目一律返回统一形状，in_bank=false 表示只存在于卷子里。"""
    return ok(exam_bank.paper_detail(paper_id))


@router.post("/exams/{exam}/subjects/{subject}/grade")
async def grade(exam: str, subject: str, body: GradeIn):
    """批量判分（无状态）。

    客观题给 CORRECT/INCORRECT；主观题给 UNGRADED 并回放参考解法。
    无副作用 → 超时后可以原样重试，不需要 Idempotency-Key。
    """
    return ok(exam_bank.grade(
        exam, subject, [a.model_dump(exclude_none=True) for a in body.answers],
    ))
