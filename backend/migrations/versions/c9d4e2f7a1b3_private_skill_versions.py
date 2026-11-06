"""let a skill version belong to one workspace; note when each browser was last seen

Versions a visitor's chat creates or repairs may hold that visitor's data (worked examples, the input that broke
the skill), so they stay in that workspace. Existing versions, built-in skills and the owner's stay shared (NULL).
RLS is turned on for every table already; this adds no table.

Revision ID: c9d4e2f7a1b3
Revises: b3e8f1c6d2a9
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d4e2f7a1b3"
down_revision: str | Sequence[str] | None = "b3e8f1c6d2a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skill_versions", sa.Column("workspace_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_skill_versions_workspace", "skill_versions", "workspaces", ["workspace_id"], ["id"],
                          ondelete="CASCADE")
    op.create_index("ix_skill_versions_workspace_id", "skill_versions", ["workspace_id"])
    op.add_column("browser_keys", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("browser_keys", "last_seen_at")
    op.drop_index("ix_skill_versions_workspace_id", table_name="skill_versions")
    op.drop_constraint("fk_skill_versions_workspace", "skill_versions", type_="foreignkey")
    op.drop_column("skill_versions", "workspace_id")
