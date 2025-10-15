"""Add recharge_orders table for T071

Revision ID: 20251015_003
Revises: 20251015_002
Create Date: 2025-10-15 10:30:00.000000

Description:
    添加充值订单表(recharge_orders),支持在线充值功能(T071)。

    功能:
    - 记录充值订单信息(金额、支付方式、二维码URL)
    - 跟踪订单状态(pending/success/failed/expired)
    - 支持微信支付和支付宝两种支付方式
    - 订单30分钟自动过期
    - 支持支付回调更新订单状态

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251015_003'
down_revision: Union[str, None] = '20251015_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recharge_orders table."""

    # Create recharge_orders table
    op.create_table(
        'recharge_orders',

        # 主键
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键UUID'),

        # 订单信息
        sa.Column('order_id', sa.String(128), nullable=False, comment='订单ID(业务键): ord_recharge_<timestamp>_<uuid>'),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False, comment='运营商ID'),
        sa.Column('amount', sa.DECIMAL(10, 2), nullable=False, comment='充值金额(10-10000元)'),
        sa.Column('payment_method', sa.String(32), nullable=False, comment='支付方式: wechat/alipay'),

        # 支付信息
        sa.Column('qr_code_url', sa.String(512), nullable=False, comment='支付二维码URL'),
        sa.Column('payment_url', sa.String(512), nullable=True, comment='支付页面URL(H5场景)'),
        sa.Column('transaction_id', sa.String(128), nullable=True, comment='支付平台交易ID(回调后填充)'),

        # 订单状态
        sa.Column('status', sa.String(32), nullable=False, server_default='pending',
                  comment='订单状态: pending(待支付)/success(已支付)/failed(支付失败)/expired(已过期)'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False, comment='订单过期时间(创建后30分钟)'),
        sa.Column('paid_at', sa.TIMESTAMP(timezone=True), nullable=True, comment='支付完成时间(回调后填充)'),

        # 错误信息(失败时)
        sa.Column('error_code', sa.String(64), nullable=True, comment='错误码(status=failed时)'),
        sa.Column('error_message', sa.String(512), nullable=True, comment='错误信息(status=failed时)'),

        # 审计字段
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP'), comment='更新时间'),

        # 主键约束
        sa.PrimaryKeyConstraint('id', name='pk_recharge_orders'),

        # 外键约束
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'],
                                name='fk_recharge_operator', ondelete='RESTRICT'),

        # CHECK约束
        sa.CheckConstraint('amount >= 10.00 AND amount <= 10000.00', name='chk_recharge_amount_range'),
        sa.CheckConstraint("payment_method IN ('wechat', 'alipay')", name='chk_payment_method'),
        sa.CheckConstraint("status IN ('pending', 'success', 'failed', 'expired')", name='chk_order_status'),
    )

    # 创建索引
    # 唯一索引: order_id业务键
    op.create_index('idx_order_id', 'recharge_orders', ['order_id'], unique=True)

    # 复合索引: 查询运营商订单(按时间降序)
    op.create_index('idx_recharge_operator', 'recharge_orders', ['operator_id', 'created_at'])

    # 普通索引: 按状态查询
    op.create_index('idx_recharge_status', 'recharge_orders', ['status'])


def downgrade() -> None:
    """Drop recharge_orders table."""

    # 删除索引
    op.drop_index('idx_recharge_status', table_name='recharge_orders')
    op.drop_index('idx_recharge_operator', table_name='recharge_orders')
    op.drop_index('idx_order_id', table_name='recharge_orders')

    # 删除表
    op.drop_table('recharge_orders')
