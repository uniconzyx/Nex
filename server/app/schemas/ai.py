from pydantic import BaseModel, Field


class ConversationIn(BaseModel):
    mode: str  # socratic / diagnose / review / interview / plan / dl_guide
    chapter_id: int | None = None
    title: str = Field(default="新对话", max_length=200)


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    attach: dict | None = None  # 可带 submission_id 等上下文引用


# ---- Phase 6 新增 ----

class ChatIn(BaseModel):
    """与 Flutter /ai/chat 契约对齐：单条消息 + 前端维护的 history。"""

    mode: str = "socratic"
    message: str = Field(min_length=1, max_length=8000)
    history: list[dict] = Field(default_factory=list)  # [{role, content}]
    chapter_id: int | None = None
    attach: dict | None = None
    conversation_id: int | None = None  # 不传则自动新建会话


class QuizIn(BaseModel):
    n: int = Field(default=5, ge=1, le=20)
    chapter_ids: list[int] | None = None  # 限定章节；不传则用薄弱章节
    types: list[str] | None = None  # 限定题型；不传则用薄弱题型


class QuizQuestionOut(BaseModel):
    exercise_id: int
    type: str
    title: str
    prompt: str
    options: list | None = None
    difficulty: str
    subject: str = ""
    source_ref: str
    chapter_id: int | None = None


class QuizOut(BaseModel):
    questions: list[QuizQuestionOut]
    based_on_weak: bool  # 是否基于用户薄弱点生成


class InsightOut(BaseModel):
    weak_chapters: list[dict]
    weak_types: list[dict]
    recommendations: list[str]
    total_wrong: int


class PlanGenerateIn(BaseModel):
    direction: str  # exam / job / dl
    weekly_hours: int = Field(default=7, ge=1, le=80)
    weeks: int = Field(default=12, ge=1, le=52)
