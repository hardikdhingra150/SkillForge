from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class BrowserKey(Base):
    """A browser's private workspace (AUTH_MODE=browser). The browser keeps a random key; only its SHA-256 is stored."""

    __tablename__ = "browser_keys"

    key_hash = mapped_column(String(64), primary_key=True)
    workspace_id = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # Updated at most once a day, so idle workspaces can be cleaned up (services/retention.py).
    last_seen_at = mapped_column(DateTime(timezone=True), nullable=True)
