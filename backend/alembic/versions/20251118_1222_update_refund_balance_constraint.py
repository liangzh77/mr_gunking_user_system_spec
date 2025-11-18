"""Update refund balance constraint to support positive refund amounts

Revision ID: 20251118_1222
Revises: 0d2de760ff79
Create Date: 2025-11-18 12:22:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251118_1222'
down_revision = '0d2de760ff79'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 检查约束是否存在再删除
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 获取表的约束
    constraints = inspector.get_check_constraints('transaction_records')
    constraint_names = [c['name'] for c in constraints]

    if 'chk_balance_calc' in constraint_names:
        # Drop the old constraint
        op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')
    else:
        print("Constraint 'chk_balance_calc' not found, skipping drop")

    # 先检查并修复不符合约束的数据
    print("Checking refund transaction data...")

    # 检查当前退款记录的amount值分布
    result = op.execute("""
        SELECT
            COUNT(*) as total_refunds,
            COUNT(*) FILTER (WHERE amount > 0) as positive_amounts,
            COUNT(*) FILTER (WHERE amount < 0) as negative_amounts,
            COUNT(*) FILTER (WHERE amount = 0) as zero_amounts
        FROM transaction_records
        WHERE transaction_type = 'refund'
    """)
    stats = result.fetchone()
    print(f"Refund statistics: total={stats[0]}, positive={stats[1]}, negative={stats[2]}, zero={stats[3]}")

    # 修复负数的退款金额
    if stats[2] > 0:
        print(f"Converting {stats[2]} negative refund amounts to positive...")
        op.execute("""
            UPDATE transaction_records
            SET amount = ABS(amount)
            WHERE transaction_type = 'refund' AND amount < 0
        """)
        print("✓ Fixed negative refund amounts")

    # 检查balance计算是否正确
    result = op.execute("""
        SELECT COUNT(*) as count
        FROM transaction_records
        WHERE transaction_type = 'refund'
        AND balance_after != balance_before - ABS(amount)
    """)
    problematic_count = result.fetchone()[0]

    if problematic_count > 0:
        print(f"⚠ Warning: Found {problematic_count} refund records with incorrect balance")
        # 暂时不自动修复,先添加约束让其失败,这样可以人工检查
        # 可以通过查看错误信息来确定是否需要修复

    # 添加新的约束 (退款amount必须是正数, balance_after = balance_before - amount)
    print("Adding new balance calculation constraint...")
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        """
        (transaction_type != 'refund' AND balance_after = balance_before + amount) OR
        (transaction_type = 'refund' AND balance_after = balance_before - amount AND amount > 0)
        """
    )
    print("✓ Successfully added new constraint")


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')

    # Restore the old constraint
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        'balance_after = balance_before + amount'
    )
