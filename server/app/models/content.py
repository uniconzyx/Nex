from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import CodeLang, CodeStd, DLFramework, DLModuleType, LessonType


class Course(IDMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(20), unique=True)  # cpp / clang
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="course")


class Chapter(IDMixin, TimestampMixin, Base):
    __tablename__ = "chapters"

    course_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("courses.id"))
    idx: Mapped[int] = mapped_column(Integer)  # 0-19 / 0-6
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # cpp-ch03
    title: Mapped[str] = mapped_column(String(100))
    goals: Mapped[list] = mapped_column(JSONB, default=list)  # 学习目标数组
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False)  # 游客可浏览
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    course: Mapped[Course] = relationship(back_populates="chapters")


class Lesson(IDMixin, TimestampMixin, Base):
    """概念讲解 / 避坑指南 / 可运行代码示例（type=example）统一载体。"""

    __tablename__ = "lessons"

    chapter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chapters.id"), index=True)
    kp_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_points.id"), nullable=True
    )
    type: Mapped[LessonType] = mapped_column(Enum(LessonType, name="lesson_type"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content_md: Mapped[str] = mapped_column(Text, default="")
    code: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_lang: Mapped[CodeLang | None] = mapped_column(Enum(CodeLang, name="code_lang"), nullable=True)
    code_std: Mapped[CodeStd | None] = mapped_column(Enum(CodeStd, name="code_std"), nullable=True)
    stdin: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgePoint(IDMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_points"

    chapter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chapters.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1-5
    sort: Mapped[int] = mapped_column(Integer, default=0)


class MindMapNode(IDMixin, TimestampMixin, Base):
    __tablename__ = "mind_map_nodes"

    chapter_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("chapters.id"), nullable=True, index=True
    )
    kp_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_points.id"), nullable=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("mind_map_nodes.id"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(200))
    pos_x: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    pos_y: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    # 注意：节点四态（mastered/learning/unlearned/weak）不落库，由 progress 推导


class DeepLearningModule(IDMixin, TimestampMixin, Base):
    """第 12-14 章的 DL 扩展表（chapter_id 唯一），正文仍走 lessons。"""

    __tablename__ = "deep_learning_modules"

    chapter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chapters.id"), unique=True)
    type: Mapped[DLModuleType] = mapped_column(Enum(DLModuleType, name="dl_module_type"))
    framework: Mapped[DLFramework | None] = mapped_column(
        Enum(DLFramework, name="dl_framework"), nullable=True
    )
    content_md: Mapped[str] = mapped_column(Text, default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
