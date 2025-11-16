"""add bank_transfer_applications table

Revision ID: d9f8e7c6b5a4
Revises: c6eb37ef2991
Create Date: 2025-11-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

# revision identifiers, used by Alembic.
revision: str = 'd9f8e7c6b5a4'
down_revision: Union[str, None] = 'c6eb37ef2991'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bank_transfer_applications table for operator bank transfer recharge requests."""

    # Create bank_transfer_applications table
    op.create_table(
        'bank_transfer_applications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), comment='主键'),
        sa.Column('operator_id', UUID(as_uuid=True), sa.ForeignKey('operator_accounts.id', ondelete='RESTRICT'), nullable=False, comment='运营商ID'),
        sa.Column('amount', sa.DECIMAL(10, 2), nullable=False, comment='申请充值金额'),
        sa.Column('voucher_image_url', sa.Text(), nullable=False, comment='转账凭证图片URL'),
        sa.Column('remark', sa.Text(), nullable=True, comment='申请备注(可选,最多500字符)'),
        sa.Column('status', sa.String(32), server_default='pending', nullable=False, comment='审核状态: pending/approved/rejected'),
        sa.Column('reject_reason', sa.Text(), nullable=True, comment='拒绝原因(status=rejected时必填)'),
        sa.Column('reviewed_by', UUID(as_uuid=True), sa.ForeignKey('finance_accounts.id', ondelete='SET NULL'), nullable=True, comment='审核人ID(财务人员)'),
        sa.Column('reviewed_at', TIMESTAMP(timezone=True), nullable=True, comment='审核时间'),
        sa.Column('created_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='申请时间'),
        sa.Column('updated_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='更新时间'),
        comment='银行转账充值申请表'
    )

    # Add CHECK constraints
    op.create_check_constraint(
        'chk_bank_transfer_status',
        'bank_transfer_applications',
        "status IN ('pending', 'approved', 'rejected')"
    )

    op.create_check_constraint(
        'chk_bank_transfer_amount_positive',
        'bank_transfer_applications',
        'amount > 0'
    )

    op.create_check_constraint(
        'chk_bank_transfer_reviewed_required',
        'bank_transfer_applications',
        "(status = 'pending') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)"
    )

    op.create_check_constraint(
        'chk_bank_transfer_reject_reason_required',
        'bank_transfer_applications',
        "(status != 'rejected') OR (reject_reason IS NOT NULL)"
    )

    # Create indexes for bank_transfer_applications
    op.create_index('idx_bank_transfer_operator', 'bank_transfer_applications', ['operator_id', 'created_at'])
    op.create_index('idx_bank_transfer_status', 'bank_transfer_applications', ['status', 'created_at'])
    op.create_index('idx_bank_transfer_reviewer', 'bank_transfer_applications', ['reviewed_by'])


def downgrade() -> None:
    """Drop bank_transfer_applications table."""

    # Drop indexes
    op.drop_index('idx_bank_transfer_reviewer', table_name='bank_transfer_applications')
    op.drop_index('idx_bank_transfer_status', table_name='bank_transfer_applications')
    op.drop_index('idx_bank_transfer_operator', table_name='bank_transfer_applications')

    # Drop table
    op.drop_table('bank_transfer_applications')
