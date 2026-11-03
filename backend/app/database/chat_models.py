from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    workspace_id = mapped_column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    title = mapped_column(String(200), nullable=False)
    provider = mapped_column(String(20), nullable=False)
    model = mapped_column(String(80), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    conversation_id = mapped_column(Uuid, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = mapped_column(Integer, nullable=False)
    role = mapped_column(String(20), nullable=False)
    content = mapped_column(Text, nullable=False, server_default="")
    # pending while the agent works on a reply; steps are appended as it goes.
    status = mapped_column(String(20), nullable=False, server_default="done")
    provider = mapped_column(String(20), nullable=True)
    model = mapped_column(String(80), nullable=True)
    steps_json = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # The skill the agent used or created for this reply, and its output.
    skill_json = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_chat_messages_sequence"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        CheckConstraint("status IN ('pending', 'done', 'failed')", name="ck_chat_messages_status"),
    )
