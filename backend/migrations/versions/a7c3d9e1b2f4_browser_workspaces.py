"""replace sign-in accounts with private browser workspaces

Revision ID: a7c3d9e1b2f4
Revises: f1a2b3c4d5e6
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3d9e1b2f4"
down_revision: str | Sequence[str] | None = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.create_table(
        "browser_keys",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_browser_keys_workspace",
                                ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("key_hash", name="pk_browser_keys"),
        sa.UniqueConstraint("workspace_id", name="uq_browser_keys_workspace"),
    )


def downgrade() -> None:
    op.drop_table("browser_keys")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("name", sa.String(length=120), server_default="", nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("email = lower(email) AND position('@' in email) > 1", name="ck_users_email"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
