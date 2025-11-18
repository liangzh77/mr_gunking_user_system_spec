"""fix_refund_balance_calculation

Revision ID: 0e7c265f1ad8
Revises: 20251118_1500
Create Date: 2025-11-18 08:28:44.015879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e7c265f1ad8'
down_revision: Union[str, None] = '20251118_1500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除旧约束
    print("Updating balance calculation constraint...")
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')

    # 添加新约束：
    # - 所有amount必须是正数
    # - 充值: balance_after = balance_before + amount
    # - 消费: balance_after = balance_before - amount
    # - 退款: balance_after = balance_before - amount
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        """
        amount > 0 AND (
            (transaction_type = 'recharge' AND balance_after = balance_before + amount) OR
            (transaction_type = 'consumption' AND balance_after = balance_before - amount) OR
            (transaction_type = 'refund' AND balance_after = balance_before - amount)
        )
        """
    )

    print("✓ Updated constraint with correct refund logic")


def downgrade() -> None:
    # 恢复退款记录
    op.execute("""
        UPDATE transaction_records
        SET balance_after = balance_before + amount
        WHERE transaction_type = 'refund' AND balance_after = balance_before - amount
    """)

    # 恢复旧约束
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        """
        amount > 0 AND (
            (transaction_type = 'recharge' AND balance_after = balance_before + amount) OR
            (transaction_type = 'consumption' AND balance_after = balance_before - amount) OR
            (transaction_type = 'refund' AND balance_after = balance_before + amount)
        )
        """
    )
