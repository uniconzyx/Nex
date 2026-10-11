from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import (
    Direction,
    NoteTarget,
    PlanGenerator,
    PlanStatus,
    QuestionType,
    TaskStatus,
    TaskTarget,
)


class Progress(TimestampMixin, Base):
    """知识点掌握度。导图四态、章节完成度均由本表聚合推导。"""

    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "kp_id", name="uq_progress_user_kp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    kp_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    mastery: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0未学 1学过 2掌握 3精通
    last_studied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Note(IDMixin, TimestampMixin, Base):
    __tablename__ = "notes"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[NoteTarget] = mapped_column(Enum(NoteTarget, name="note_target"))
    target_id: Mapped[int] = mapped_column(BigInteger)
    content_md: Mapped[str] = mapped_column(Text, default="")


class WrongQuestion(TimestampMixin, Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "question_type", "question_id", name="uq_wrong_user_q"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, name="question_type"))
    question_id: Mapped[int] = mapped_column(BigInteger)
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    right_count: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_result: Mapped[str] = mapped_column(String(10), default="wrong")  # wrong / right


class StudyPlan(IDMixin, TimestampMixin, Base):
    __tablename__ = "study_plans"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    direction: Mapped[Direction] = mapped_column(Enum(Direction, name="plan_direction"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    weekly_hours: Mapped[int] = mapped_column(Integer, default=7)
    generated_by: Mapped[PlanGenerator] = mapped_column(
        Enum(PlanGenerator, name="plan_generator"), default=PlanGenerator.ai
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus, name="plan_status"), default=PlanStatus.active)


class DailyTask(IDMixin, TimestampMixin, Base):
    __tablename__ = "daily_tasks"
    __table_args__ = (
        UniqueConstraint("plan_id", "date", "target_type", "target_id", name="uq_task_slot"),
    )

    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("study_plans.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    target_type: Mapped[TaskTarget] = mapped_column(Enum(TaskTarget, name="task_target"))
    target_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), default=TaskStatus.pending)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Achievement(IDMixin, TimestampMixin, Base):
    __tablename__ = "achievements"

    code: Mapped[str] = mapped_column(String(50), unique=True)  # first_ac / streak_7 / project_done
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(100), default="")
    condition: Mapped[dict] = mapped_column(JSONB, default=dict)


class UserAchievement(TimestampMixin, Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    achievement_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("achievements.id"))
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
