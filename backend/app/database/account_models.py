from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class User(Base):
    """A person who signs in (AUTH_MODE=accounts). Each user owns one workspace."""

    __tablename__ = "users"

    id = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    email = mapped_column(String(254), nullable=False, unique=True)  # stored lower-cased
    name = mapped_column(String(120), nullable=False, server_default="")
    password_hash = mapped_column(String(200), nullable=False)
    workspace_id = mapped_column(Uuid, ForeignKey("workspaces.id"), nullable=False, unique=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (CheckConstraint("email = lower(email) AND position('@' in email) > 1", name="ck_users_email"),)


class UserSession(Base):
    """A signed-in browser. Only the SHA-256 of the token is stored."""

    __tablename__ = "user_sessions"

    token_hash = mapped_column(String(64), primary_key=True)
    user_id = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
