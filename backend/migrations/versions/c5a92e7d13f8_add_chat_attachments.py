"""add chat attachments

Revision ID: c5a92e7d13f8
Revises: b8e3d1f04c52
Create Date: 2026-11-03 19:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c5a92e7d13f8'
down_revision: str | Sequence[str] | None = 'b8e3d1f04c52'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'chat_attachments',
        sa.Column('id', sa.Uuid(), server_default=sa.text('uuidv7()'), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('message_id', sa.Uuid(), nullable=True),
        sa.Column('filename', sa.String(length=200), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('content_bytes', sa.LargeBinary(), nullable=False),
        sa.Column('headers_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('preview_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_attachments_conversation_id'), 'chat_attachments', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_attachments_message_id'), 'chat_attachments', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_attachments_message_id'), table_name='chat_attachments')
    op.drop_index(op.f('ix_chat_attachments_conversation_id'), table_name='chat_attachments')
    op.drop_table('chat_attachments')
