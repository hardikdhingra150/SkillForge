"""add model outcomes for the scoreboard

Revision ID: b8e3d1f04c52
Revises: a41f6c2e9b07
Create Date: 2026-11-03 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b8e3d1f04c52'
down_revision: str | Sequence[str] | None = 'a41f6c2e9b07'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = "('planner', 'author', 'verifier')"
EVENTS = ("('proven', 'rejected', 'exhausted', 'overruled', 'example_corrected', 'reused', "
          "'agreed', 'disagreed', 'escalated')")


def upgrade() -> None:
    op.create_table(
        'model_outcomes',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=80), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('event', sa.String(length=30), nullable=False),
        sa.Column('capability', sa.String(length=80), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(f'role IN {ROLES}', name='ck_model_outcomes_role'),
        sa.CheckConstraint(f'event IN {EVENTS}', name='ck_model_outcomes_event'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_model_outcomes_provider'), 'model_outcomes', ['provider'], unique=False)
    op.create_index(op.f('ix_model_outcomes_capability'), 'model_outcomes', ['capability'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_model_outcomes_capability'), table_name='model_outcomes')
    op.drop_index(op.f('ix_model_outcomes_provider'), table_name='model_outcomes')
    op.drop_table('model_outcomes')
