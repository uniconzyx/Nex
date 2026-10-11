from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import CodeStd, SubmissionStatus


class Submission(IDMixin, TimestampMixin, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        Index("ix_submissions_user_created", "user_id", "created_at"),
        Index("ix_submissions_exercise_status", "exercise_id", "status"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    # 可空 = 自由运行台（无题目归属）
    exercise_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("exercises.id"), nullable=True
    )
    lang: Mapped[CodeStd] = mapped_column(Enum(CodeStd, name="submission_lang"))
    source_code: Mapped[str] = mapped_column(Text)
    stdin: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"), default=SubmissionStatus.queued, index=True
    )
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge0_token: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 逗号分隔多 token
    passed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnosis_md: Mapped[str | None] = mapped_column(Text, nullable=True)
