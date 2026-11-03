"""allow imported skill origin

Revision ID: d7f30b9a6e21
Revises: c5a92e7d13f8
Create Date: 2026-11-03 20:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'd7f30b9a6e21'
down_revision: str | Sequence[str] | None = 'c5a92e7d13f8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint('ck_skill_versions_origin', 'skill_versions', type_='check')
    op.create_check_constraint(
        'ck_skill_versions_origin', 'skill_versions', "origin IN ('builtin', 'generated', 'repaired', 'imported')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_skill_versions_origin', 'skill_versions', type_='check')
    op.create_check_constraint(
        'ck_skill_versions_origin', 'skill_versions', "origin IN ('builtin', 'generated', 'repaired')",
    )
