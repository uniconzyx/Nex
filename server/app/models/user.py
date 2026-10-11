from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import Direction, Plan, Theme, UserRole, UserStatus


class User(IDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.user)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), default=UserStatus.active
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    nickname: Mapped[str] = mapped_column(String(50), default="")
    avatar_url: Mapped[str] = mapped_column(String(512), default="")
    direction: Mapped[Direction | None] = mapped_column(
        Enum(Direction, name="direction"), nullable=True
    )
    daily_minutes: Mapped[int] = mapped_column(default=60)
    plan: Mapped[Plan] = mapped_column(Enum(Plan, name="plan_type"), default=Plan.free)
    theme: Mapped[Theme] = mapped_column(Enum(Theme, name="theme"), default=Theme.system)
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    font_scale: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)

    user: Mapped[User] = relationship(back_populates="profile")


class OAuthIdentity(TimestampMixin, Base):
    __tablename__ = "user_oauth_identities"
    __table_args__ = (UniqueConstraint("provider", "openid", name="uq_oauth_provider_openid"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(20))  # wechat / qq / github
    openid: Mapped[str] = mapped_column(String(128))
