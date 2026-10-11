from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import Difficulty, ProjectCategory


class Project(IDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    chapter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chapters.id"), index=True)
    category: Mapped[ProjectCategory] = mapped_column(Enum(ProjectCategory, name="project_category"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    requirement_md: Mapped[str] = mapped_column(Text, default="")
    architecture_md: Mapped[str] = mapped_column(Text, default="")
    deploy_md: Mapped[str] = mapped_column(Text, default="")
    interview_md: Mapped[str] = mapped_column(Text, default="")  # 面试问法
    template_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # MinIO tar 包
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty, name="project_difficulty"), default=Difficulty.mid)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks: Mapped[list["ProjectTask"]] = relationship(back_populates="project")


class ProjectTask(IDMixin, TimestampMixin, Base):
    __tablename__ = "project_tasks"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    order_no: Mapped[int] = mapped_column(Integer, default=0)
    verification: Mapped[dict] = mapped_column(JSONB, default=dict)  # 步骤验收/测试说明

    project: Mapped[Project] = relationship(back_populates="tasks")


class ProjectTaskProgress(TimestampMixin, Base):
    __tablename__ = "project_task_progress"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_user_task"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("project_tasks.id", ondelete="CASCADE"))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
