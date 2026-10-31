from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
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
from app.models.types import JSONType


class Progress(TimestampMixin, Base):
    """知识点掌握度。导图四态、章节完成度均由本表聚合推导。"""

    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "kp_id", name="uq_progress_user_kp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    kp_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("knowledge_points.id", ondelete="CASCADE"))
    mastery: Mapped[int] = mapped_column(SmallInteger, default=0)  # 0未学 1学过 2掌握 3精通
    last_studied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StudyState(TimestampMixin, Base):
    """本机体验快照（与前端 localStorage["kaimao.progress.v1"] 对齐）。

    为什么单独建表而不是塞进 progress：
      progress 是"知识点掌握度"，粒度到 kp，服务于导图四态与复习调度；
      前端记的是"章节是否点过已掌握 / 项目是否通关 / 每天是否打卡"，
      是体验层的事实，不是学习效果评估。两者混在一张表里，之后接入
      间隔复习会把语义搅乱。

    同步策略：本机是事实源，这里存的是**最近一次上传的快照**（整行覆盖），
    拉取时客户端按 (章节 ∪ 项目) 取并集合并，因此不会因为换设备丢掉进度。
    """

    __tablename__ = "study_state"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    done_chapters: Mapped[list] = mapped_column(JSONType, default=list)
    done_projects: Mapped[list] = mapped_column(JSONType, default=list)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    outfit: Mapped[str] = mapped_column(String(40), default="default")
    theme: Mapped[str] = mapped_column(String(10), default="light")
    client_rev: Mapped[int] = mapped_column(Integer, default=0)  # 客户端自增版本，便于排查冲突
    # 整份进度快照（与 auth-server /api/auth/progress 对齐）。
    # 存的是完整 ProgressState（含 answers / bestiary / chapterRuns / weekly 等），
    # 这样 Nex 后端也能做到跨设备全量恢复，不再只是 5 个扁平字段。
    # 旧数据（只走过 5 字段路径）此列为 NULL，读取时回退到去规范化字段即可。
    snapshot: Mapped[dict | None] = mapped_column(JSONType, nullable=True)


class Checkin(TimestampMixin, Base):
    """打卡记录。单独一张表而不是 JSON 数组，是为了以后按日期范围统计/排行。"""

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_checkin_user_day"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)


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
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
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
    condition: Mapped[dict] = mapped_column(JSONType, default=dict)

class UserAchievement(TimestampMixin, Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    achievement_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("achievements.id"))
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
