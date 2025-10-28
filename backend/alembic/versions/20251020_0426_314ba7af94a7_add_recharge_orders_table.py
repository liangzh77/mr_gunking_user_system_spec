"""add_recharge_orders_table

Revision ID: 314ba7af94a7
Revises: 41bc8cb3aa19
Create Date: 2025-10-20 04:26:51.778174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = '314ba7af94a7'
down_revision: Union[str, None] = '41bc8cb3aa19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recharge_orders table for payment order management."""

    # Create recharge_orders table
    op.create_table(
        'recharge_orders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='主键UUID'),
        sa.Column('order_id', sa.String(128), nullable=False, unique=True, comment='订单ID(业务键): ord_recharge_<timestamp>_<uuid>'),
        sa.Column('operator_id', UUID(as_uuid=True), sa.ForeignKey('operator_accounts.id', ondelete='RESTRICT'), nullable=False, comment='运营商ID'),
        sa.Column('amount', sa.DECIMAL(10, 2), nullable=False, comment='充值金额(10-10000元)'),
        sa.Column('payment_method', sa.String(32), nullable=False, comment='支付方式: wechat/alipay'),
        sa.Column('qr_code_url', sa.String(512), nullable=False, comment='支付二维码URL'),
        sa.Column('payment_url', sa.String(512), nullable=True, comment='支付页面URL(H5场景)'),
        sa.Column('transaction_id', sa.String(128), nullable=True, comment='支付平台交易ID(回调后填充)'),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending', comment='订单状态: pending(待支付)/success(已支付)/failed(支付失败)/expired(已过期)'),
        sa.Column('expires_at', TIMESTAMP(timezone=True), nullable=False, comment='订单过期时间(创建后30分钟)'),
        sa.Column('paid_at', TIMESTAMP(timezone=True), nullable=True, comment='支付完成时间(回调后填充)'),
        sa.Column('error_code', sa.String(64), nullable=True, comment='错误码(status=failed时)'),
        sa.Column('error_message', sa.String(512), nullable=True, comment='错误信息(status=failed时)'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.current_timestamp(), comment='创建时间'),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.current_timestamp(), comment='更新时间'),
        comment='充值订单表'
    )

    # Add CHECK constraints
    op.create_check_constraint(
        'chk_recharge_amount_range',
        'recharge_orders',
        'amount >= 10.00 AND amount <= 10000.00'
    )

    op.create_check_constraint(
        'chk_payment_method',
        'recharge_orders',
        "payment_method IN ('wechat', 'alipay')"
    )

    op.create_check_constraint(
        'chk_order_status',
        'recharge_orders',
        "status IN ('pending', 'success', 'failed', 'expired')"
    )

    # Create indexes
    op.create_index('idx_order_id', 'recharge_orders', ['order_id'], unique=True)
    op.create_index('idx_recharge_operator', 'recharge_orders', ['operator_id', 'created_at'])
    op.create_index('idx_recharge_status', 'recharge_orders', ['status'])


def downgrade() -> None:
    """Drop recharge_orders table."""

    # Drop indexes
    op.drop_index('idx_recharge_status', table_name='recharge_orders')
    op.drop_index('idx_recharge_operator', table_name='recharge_orders')
    op.drop_index('idx_order_id', table_name='recharge_orders')

    # Drop constraints
    op.drop_constraint('chk_order_status', 'recharge_orders', type_='check')
    op.drop_constraint('chk_payment_method', 'recharge_orders', type_='check')
    op.drop_constraint('chk_recharge_amount_range', 'recharge_orders', type_='check')

    # Drop table
    op.drop_table('recharge_orders')
