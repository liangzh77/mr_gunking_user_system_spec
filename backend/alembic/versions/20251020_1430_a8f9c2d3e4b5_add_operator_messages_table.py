"""add_operator_messages_table

Create operator_messages table for notification system.
Operators will receive notifications when refunds/invoices are approved or rejected.

Revision ID: a8f9c2d3e4b5
Revises: 41bc8cb3aa19
Create Date: 2025-10-20 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = 'a8f9c2d3e4b5'
down_revision: Union[str, None] = '41bc8cb3aa19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create operator_messages table for notification system."""

    # Create operator_messages table
    op.create_table(
        'operator_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='消息ID'),
        sa.Column('operator_id', UUID(as_uuid=True), sa.ForeignKey('operator_accounts.id', ondelete='CASCADE'), nullable=False, comment='运营商ID'),
        sa.Column('message_type', sa.String(50), nullable=False, comment='消息类型: refund_approved, refund_rejected, invoice_approved, invoice_rejected, system_announcement'),
        sa.Column('title', sa.String(200), nullable=False, comment='消息标题'),
        sa.Column('content', sa.Text, nullable=False, comment='消息内容'),
        sa.Column('related_type', sa.String(50), nullable=True, comment='关联资源类型: refund, invoice, 等'),
        sa.Column('related_id', UUID(as_uuid=True), nullable=True, comment='关联资源ID'),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default='false', comment='是否已读'),
        sa.Column('read_at', TIMESTAMP(timezone=True), nullable=True, comment='阅读时间'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        comment='运营商消息通知表'
    )

    # Create indexes for operator_messages
    op.create_index('idx_operator_messages_operator_created', 'operator_messages', ['operator_id', 'created_at'])
    op.create_index('idx_operator_messages_operator_read', 'operator_messages', ['operator_id', 'is_read'])
    op.create_index('idx_operator_messages_type', 'operator_messages', ['message_type'])


def downgrade() -> None:
    """Remove operator_messages table."""

    # Drop indexes first
    op.drop_index('idx_operator_messages_type', table_name='operator_messages')
    op.drop_index('idx_operator_messages_operator_read', table_name='operator_messages')
    op.drop_index('idx_operator_messages_operator_created', table_name='operator_messages')

    # Drop table
    op.drop_table('operator_messages')
