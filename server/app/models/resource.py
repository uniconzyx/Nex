from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import (
    Difficulty,
    FavoriteTarget,
    ResourceSource,
    ResourceType,
    SyncMode,
    SyncStatus,
)

resource_chapters = Table(
    "resource_chapters",
    Base.metadata,
    Column("resource_id", BigInteger, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True),
    Column("chapter_id", BigInteger, ForeignKey("chapters.id", ondelete="CASCADE"), primary_key=True),
)


class Resource(IDMixin, TimestampMixin, Base):
    """外部资源引用（GitHub/LeetCode/牛客/文档）。合规红线：只存元数据 + 链接，不存正文。"""

    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_resource_ext"),)

    source: Mapped[ResourceSource] = mapped_column(Enum(ResourceSource, name="resource_source"), index=True)
    type: Mapped[ResourceType] = mapped_column(Enum(ResourceType, name="resource_type"))
    external_id: Mapped[str] = mapped_column(String(128))  # leetcode:1 / github:owner/repo
    title: Mapped[str] = mapped_column(String(300))
    title_cn: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(512))
    difficulty: Mapped[Difficulty | None] = mapped_column(
        Enum(Difficulty, name="resource_difficulty"), nullable=True
    )
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    license: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)  # tags、面经公司等非标字段
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncJob(IDMixin, TimestampMixin, Base):
    __tablename__ = "sync_jobs"

    source: Mapped[ResourceSource] = mapped_column(Enum(ResourceSource, name="sync_source"))
    status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus, name="sync_status"), default=SyncStatus.running)
    mode: Mapped[SyncMode] = mapped_column(Enum(SyncMode, name="sync_mode"), default=SyncMode.incremental)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)  # created/updated/failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Favorite(TimestampMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorite_target"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[FavoriteTarget] = mapped_column(Enum(FavoriteTarget, name="favorite_target"))
    target_id: Mapped[int] = mapped_column(BigInteger)
