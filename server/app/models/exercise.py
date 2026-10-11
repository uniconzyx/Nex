from sqlalchemy import BigInteger, Boolean, Column, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import Difficulty, ExerciseSource, ExerciseType

exercise_tags = Table(
    "exercise_tags",
    Base.metadata,
    Column("exercise_id", BigInteger, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

interview_question_tags = Table(
    "interview_question_tags",
    Base.metadata,
    Column("question_id", BigInteger, ForeignKey("interview_questions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(IDMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    category: Mapped[str] = mapped_column(String(20), default="topic")  # syntax/ds/algo/topic/company


class Exercise(IDMixin, TimestampMixin, Base):
    __tablename__ = "exercises"

    chapter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chapters.id"), index=True)
    type: Mapped[ExerciseType] = mapped_column(Enum(ExerciseType, name="exercise_type"), index=True)
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, name="difficulty"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content_md: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # 选择题选项
    answer: Mapped[dict] = mapped_column(JSONB, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[ExerciseSource] = mapped_column(
        Enum(ExerciseSource, name="exercise_source"), default=ExerciseSource.self_
    )
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256)
    is_daily_eligible: Mapped[bool] = mapped_column(Boolean, default=False)

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="exercise")
    tags: Mapped[list[Tag]] = relationship(secondary=exercise_tags)


class TestCase(IDMixin, TimestampMixin, Base):
    __tablename__ = "test_cases"

    exercise_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    input: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, default="")
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)  # 非示例用例对前端不可见
    sort: Mapped[int] = mapped_column(Integer, default=0)

    exercise: Mapped[Exercise] = relationship(back_populates="test_cases")


class InterviewQuestion(IDMixin, TimestampMixin, Base):
    __tablename__ = "interview_questions"

    chapter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chapters.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer_md: Mapped[str] = mapped_column(Text, default="")
    follow_ups: Mapped[list] = mapped_column(JSONB, default=list)  # 面试官追问链
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, name="iq_difficulty"), default=Difficulty.mid)
    source: Mapped[str] = mapped_column(String(20), default="self")
    company_tags: Mapped[list] = mapped_column(JSONB, default=list)

    tags: Mapped[list[Tag]] = relationship(secondary=interview_question_tags)
