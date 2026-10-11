from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import IDMixin, TimestampMixin
from app.models.enums import AIMode, MessageRole


class AIConversation(IDMixin, TimestampMixin, Base):
    __tablename__ = "ai_conversations"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[AIMode] = mapped_column(Enum(AIMode, name="ai_mode"))
    chapter_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("chapters.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    context_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)  # 章节/代码/错题/进度快照

    messages: Mapped[list["AIMessage"]] = relationship(back_populates="conversation")


class AIMessage(IDMixin, TimestampMixin, Base):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(50), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)

    conversation: Mapped[AIConversation] = relationship(back_populates="messages")
