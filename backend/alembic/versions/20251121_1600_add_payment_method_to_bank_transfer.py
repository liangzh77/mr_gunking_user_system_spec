"""add_payment_method_to_bank_transfer

Revision ID: 20251121_1600
Revises: 20251118_1926
Create Date: 2025-11-21 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251121_1600'
down_revision: Union[str, None] = '20251118_1926'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 payment_method 字段,默认值为 'bank_transfer'
    op.add_column(
        'bank_transfer_applications',
        sa.Column(
            'payment_method',
            sa.String(32),
            nullable=False,
            server_default='bank_transfer',
            comment='支付方式: bank_transfer/wechat'
        )
    )


def downgrade() -> None:
    # 删除 payment_method 字段
    op.drop_column('bank_transfer_applications', 'payment_method')
