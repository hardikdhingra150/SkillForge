from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import mapped_column

from app.database.models import Base


class Connector(Base):
    """A visitor's computer, paired with their workspace, that runs their own Claude Code or Codex for them.

    The program on their computer keeps a random token (sfc_...); only its SHA-256 is stored. One per workspace.
    """

    __tablename__ = "connectors"

    token_hash = mapped_column(String(64), primary_key=True)
    workspace_id = mapped_column(Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
