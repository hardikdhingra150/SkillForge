"""store skill source, contract and lineage

Revision ID: 7c2d9e4b1a30
Revises: 5e85a44694b5
Create Date: 2026-11-03 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '7c2d9e4b1a30'
down_revision: str | Sequence[str] | None = '5e85a44694b5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('skill_versions', sa.Column('source_code', sa.Text(), nullable=True))
    op.add_column('skill_versions', sa.Column('contract_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('skill_versions', sa.Column('origin', sa.String(length=20), server_default='builtin', nullable=False))
    op.add_column('skill_versions', sa.Column('parent_version', sa.String(length=32), nullable=True))
    op.add_column('skill_versions', sa.Column('change_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_check_constraint(
        'ck_skill_versions_origin', 'skill_versions', "origin IN ('builtin', 'generated', 'repaired')",
    )
    # Source and contract are stored together, or not at all (legacy in-repo skills).
    op.create_check_constraint(
        'ck_skill_versions_source_contract', 'skill_versions', '(source_code IS NULL) = (contract_json IS NULL)',
    )


def downgrade() -> None:
    op.drop_constraint('ck_skill_versions_source_contract', 'skill_versions', type_='check')
    op.drop_constraint('ck_skill_versions_origin', 'skill_versions', type_='check')
    op.drop_column('skill_versions', 'change_json')
    op.drop_column('skill_versions', 'parent_version')
    op.drop_column('skill_versions', 'origin')
    op.drop_column('skill_versions', 'contract_json')
    op.drop_column('skill_versions', 'source_code')
