"""学习/考研指南（外部笔记仓库的结构化索引）。

为什么单独建表而不是塞进 `resources`：
  - `resources` 是「一个仓库一条记录」，用于推荐与同步；
  - 指南是「一个仓库里的一篇篇笔记」，需要按学科（数学/408/英语/政治）与形态
    （笔记/经验贴/外链）筛选，还要能标推荐、预估阅读时长。

合规：只存「索引 + 要点提炼 + 原文链接」，不搬运正文与图片。
408 单篇笔记最大 44MB 且依赖同目录 assets，整篇入库既超限也会断图。
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import GuideKind
from app.models.types import JSONType

class GuideSource(IDMixin, TimestampMixin, Base):
    """指南来源仓库，一个来源一个导航分组。"""

    __tablename__ = "guide_sources"

    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    repo: Mapped[str] = mapped_column(String(200), default="")
    repo_url: Mapped[str] = mapped_column(String(512), default="")
    license: Mapped[str | None] = mapped_column(String(40), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    updated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    # [{"key":"cs408","label":"408 专业课"}] —— 学科中文名只在这里维护一份
    subjects: Mapped[list] = mapped_column(JSONType, default=list)

    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class GuideItem(IDMixin, TimestampMixin, Base):
    """一篇笔记 / 一条经验贴 / 一个外链。"""

    __tablename__ = "guide_items"

    source_key: Mapped[str] = mapped_column(String(40), index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    kind: Mapped[GuideKind] = mapped_column(Enum(GuideKind, name="guide_kind"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)

    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    points: Mapped[list] = mapped_column(JSONType, default=list)
    read_min: Mapped[int] = mapped_column(Integer, default=5)
    recommended: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    source_path: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
