"""add_deduct_transaction_type

Revision ID: 20251118_1926
Revises: 0e7c265f1ad8
Create Date: 2025-11-18 19:26:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251118_1926'
down_revision: Union[str, None] = '0e7c265f1ad8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除旧的交易类型约束
    print("Dropping old transaction type constraint...")
    op.drop_constraint('chk_trans_type', 'transaction_records', type_='check')

    # 2. 添加新的交易类型约束(包含deduct)
    print("Adding new transaction type constraint with 'deduct'...")
    op.create_check_constraint(
        'chk_trans_type',
        'transaction_records',
        "transaction_type IN ('recharge', 'consumption', 'refund', 'deduct')"
    )

    # 3. 修复旧的refund记录(将balance_after < balance_before的refund改为deduct)
    print("Migrating old refund records that decrease balance to deduct type...")
    op.execute("""
        UPDATE transaction_records
        SET transaction_type = 'deduct'
        WHERE transaction_type = 'refund' AND balance_after < balance_before
    """)

    # 4. 删除旧的余额计算约束
    print("Dropping old balance calculation constraint...")
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')

    # 4. 添加新的余额计算约束
    # 充值/退款: balance_after = balance_before + amount (增加余额)
    # 消费/扣费: balance_after = balance_before - amount (减少余额)
    # 所有amount必须为正数
    print("Adding new balance calculation constraint...")
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        """
        amount > 0 AND (
            (transaction_type IN ('recharge', 'refund') AND balance_after = balance_before + amount) OR
            (transaction_type IN ('consumption', 'deduct') AND balance_after = balance_before - amount)
        )
        """
    )

    print("✓ Successfully added 'deduct' transaction type")


def downgrade() -> None:
    # 1. 删除新约束
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')
    op.drop_constraint('chk_trans_type', 'transaction_records', type_='check')

    # 2. 恢复旧的交易类型约束(不含deduct)
    op.create_check_constraint(
        'chk_trans_type',
        'transaction_records',
        "transaction_type IN ('recharge', 'consumption', 'refund')"
    )

    # 3. 恢复旧的余额计算约束
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
