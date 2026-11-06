"""turn on row-level security for every table

Hosted Postgres such as Supabase publishes the public schema through a REST API that anyone with the project's
public key can call. With RLS on and no policies, that API sees no rows. SkillForge connects as the tables' owner,
which RLS doesn't apply to, so the app is unaffected. A later migration that adds a table should enable RLS on it.

Revision ID: b3e8f1c6d2a9
Revises: a7c3d9e1b2f4
"""
from collections.abc import Sequence

from alembic import op

revision: str = "b3e8f1c6d2a9"
down_revision: str | Sequence[str] | None = "a7c3d9e1b2f4"
branch_labels = None
depends_on = None

EACH_TABLE = """
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = current_schema() LOOP
    EXECUTE format('ALTER TABLE %I {action} ROW LEVEL SECURITY', t);
  END LOOP;
END $$
"""


def upgrade() -> None:
    op.execute(EACH_TABLE.replace("{action}", "ENABLE"))


def downgrade() -> None:
    op.execute(EACH_TABLE.replace("{action}", "DISABLE"))
