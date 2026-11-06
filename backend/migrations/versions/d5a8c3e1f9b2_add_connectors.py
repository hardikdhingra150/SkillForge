"""connectors: a visitor's own computer running their Claude Code or Codex

Revision ID: d5a8c3e1f9b2
Revises: c9d4e2f7a1b3
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5a8c3e1f9b2"
down_revision: str | Sequence[str] | None = "c9d4e2f7a1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connectors",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_connectors_workspace", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash", name="pk_connectors"),
        sa.UniqueConstraint("workspace_id", name="uq_connectors_workspace"),
    )
    # Like every table: closed to Supabase's public REST API (see b3e8f1c6d2a9).
    op.execute("ALTER TABLE connectors ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("connectors")
