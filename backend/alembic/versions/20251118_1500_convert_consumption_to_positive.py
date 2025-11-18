"""convert consumption amounts to positive

Revision ID: 20251118_1500
Revises: 20251118_1222
Create Date: 2025-11-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251118_1500'
down_revision = '20251118_1222'
branch_labels = None
depends_on = None


def upgrade() -> None:
    print("Converting consumption amounts from negative to positive...")

    # 将消费记录的负数金额转换为正数
    op.execute("""
        UPDATE transaction_records
        SET amount = -amount
        WHERE transaction_type = 'consumption' AND amount < 0
    """)

    print("✓ Converted all consumption amounts to positive")

    # 更新约束：所有交易类型的amount都必须是正数
    print("Updating balance calculation constraint...")

    # 删除旧约束(如果存在)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = inspector.get_check_constraints('transaction_records')
    constraint_names = [c['name'] for c in constraints]

    if 'chk_balance_calc' in constraint_names:
        op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')
        print("✓ Dropped existing constraint")
    else:
        print("⚠ Constraint 'chk_balance_calc' not found, skipping drop")

    # 添加新约束：
    # - 所有amount必须是正数
    # - 充值: balance_after = balance_before + amount
    # - 消费: balance_after = balance_before - amount
    # - 退款: balance_after = balance_before + amount
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

    print("✓ Updated constraint: all amounts must be positive")


def downgrade() -> None:
    # 回滚：将消费金额改回负数
    op.execute("""
        UPDATE transaction_records
        SET amount = -amount
        WHERE transaction_type = 'consumption' AND amount > 0
    """)

    # 恢复旧约束
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        """
        (transaction_type != 'refund' AND balance_after = balance_before + amount) OR
        (transaction_type = 'refund' AND balance_after = balance_before - amount AND amount > 0)
        """
    )
