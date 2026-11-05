"""add audit events

Revision ID: e4b9c2a7f310
Revises: d7f30b9a6e21
Create Date: 2026-11-05 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e4b9c2a7f310'
down_revision: str | Sequence[str] | None = 'd7f30b9a6e21'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIONS = ("('skill.promoted', 'skill.retired', 'skill.restored', 'skill.imported', "
           "'run.retried', 'run.rejected')")


def upgrade() -> None:
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('actor', sa.String(length=40), nullable=False),
        sa.Column('action', sa.String(length=40), nullable=False),
        sa.Column('target', sa.String(length=160), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(f'action IN {ACTIONS}', name='ck_audit_events_action'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_events_workspace_id'), 'audit_events', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_events_created_at'), table_name='audit_events')
    op.drop_index(op.f('ix_audit_events_workspace_id'), table_name='audit_events')
    op.drop_table('audit_events')
