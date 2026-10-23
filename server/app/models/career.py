"""就业级实战项目库（跨章节、来源为真实开源仓库）。

与 `projects` 表的区别：
  - `projects`  = 章节内项目，必须挂 chapter_id，用于「学完这章做这个」；
  - `career_projects` = 跨章节的就业向项目库，按学科(track)组织，元数据来自 GitHub API 实测，
    用于「为了实习/校招该练哪个项目」。

数字类字段（stars/forks/语言/许可证/最近提交）由 `scripts/merge_career_meta.py` 从 API 回填，
不手工维护，避免随时间漂移。
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import CareerTrack, Difficulty, ProjectTier
from app.models.types import CAREER_TIER, JSONType, PROJECT_DIFFICULTY

class CareerProject(IDMixin, TimestampMixin, Base):
    __tablename__ = "career_projects"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    track: Mapped[CareerTrack] = mapped_column(
        Enum(CareerTrack, name="career_track"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    repo: Mapped[str] = mapped_column(String(200), index=True)
    repo_url: Mapped[str] = mapped_column(String(512), default="")

    # 内容层（人工撰写）
    summary: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[Difficulty] = mapped_column(
        PROJECT_DIFFICULTY, default=Difficulty.mid, index=True
    )
    # 能力梯度与预计工时：t1 能跑 / t2 能写 / t3 能讲原理 / t4 能进简历
    tier: Mapped[ProjectTier] = mapped_column(
        CAREER_TIER, default=ProjectTier.t1, index=True
    )
    hours: Mapped[int] = mapped_column(Integer, default=0)
    stack: Mapped[list] = mapped_column(JSONType, default=list)
    learn: Mapped[list] = mapped_column(JSONType, default=list)
    career_value: Mapped[str] = mapped_column(Text, default="")
    accept: Mapped[list] = mapped_column(JSONType, default=list)
    interview: Mapped[list] = mapped_column(JSONType, default=list)

    # 仓库事实层（API 回填）
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    license: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_pushed: Mapped[date | None] = mapped_column(Date, nullable=True)
    size_kb: Mapped[int] = mapped_column(Integer, default=0)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    repo_desc: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[list] = mapped_column(JSONType, default=list)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)

    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    steps: Mapped[list["CareerProjectStep"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

class CareerProjectStep(IDMixin, TimestampMixin, Base):
    """复现步骤。单独建表而非塞 JSONType，是为了支持逐步骤打卡。"""

    __tablename__ = "career_project_steps"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("career_projects.id", ondelete="CASCADE"), index=True
    )
    order_no: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(400))
    description: Mapped[str] = mapped_column(Text, default="")
    verification: Mapped[dict] = mapped_column(JSONType, default=dict)

    project: Mapped["CareerProject"] = relationship(back_populates="steps")

class CareerStepProgress(TimestampMixin, Base):
    __tablename__ = "career_step_progress"
    __table_args__ = (UniqueConstraint("user_id", "step_id", name="uq_user_career_step"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("career_project_steps.id", ondelete="CASCADE")
    )
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class CareerRoute(IDMixin, TimestampMixin, Base):
    """岗位路线：把「可实习」拆成可核对的学科 × 梯度要求。

    与项目是多对多的逻辑关系（一条路线覆盖多个学科与梯度），但依赖内容规模固定，
    因此把学科要求存成 JSONType 而不是建关联表，避免为了 6 条路线铺一张中间表。
    """

    __tablename__ = "career_routes"

    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(Text, default="")

    # {"cpp": ["t1","t2","t3","t4"], "database": ["t1","t2"]}
    tracks: Mapped[dict] = mapped_column(JSONType, default=dict)
    t4_required: Mapped[int] = mapped_column(Integer, default=2)
    projects: Mapped[int] = mapped_column(Integer, default=0)
    hours: Mapped[int] = mapped_column(Integer, default=0)
    deliverables: Mapped[list] = mapped_column(JSONType, default=list)
    interview_bar: Mapped[list] = mapped_column(JSONType, default=list)

    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
