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
    print("Checking and fixing refund transaction data...")

    # 直接修复负数的退款金额,不需要先检查
    print("Converting any negative refund amounts to positive...")
    op.execute("""
        UPDATE transaction_records
        SET amount = ABS(amount)
        WHERE transaction_type = 'refund' AND amount < 0
    """)
    print("✓ Fixed negative refund amounts (if any)")

    # 检查是否还有不符合新约束的数据
    # 使用connection来获取结果
    from alembic import context
    connection = context.get_bind()

    result = connection.execute(sa.text("""
        SELECT COUNT(*) as count
        FROM transaction_records
        WHERE transaction_type = 'refund'
        AND (balance_after != balance_before - amount OR amount <= 0)
    """))
    problematic_count = result.scalar()

    if problematic_count and problematic_count > 0:
        print(f"⚠ Warning: Found {problematic_count} refund records that don't match new constraint")
        print("Attempting to fix these records...")

        # 显示并修复问题记录
        result = connection.execute(sa.text("""
            SELECT id, amount, balance_before, balance_after, description
            FROM transaction_records
            WHERE transaction_type = 'refund'
            AND (balance_after != balance_before - amount OR amount <= 0)
        """))

        fixed_count = 0
        for row in result:
            record_id = row[0]
            amount = row[1]
            balance_before = row[2]
            balance_after = row[3]
            expected_balance = balance_before - amount

            print(f"  Fixing ID: {record_id}")
            print(f"    Current: amount={amount}, before={balance_before}, after={balance_after}")
            print(f"    Expected after={expected_balance}")

            # 修复 balance_after
            connection.execute(sa.text("""
                UPDATE transaction_records
                SET balance_after = :expected_balance
                WHERE id = :record_id
            """), {"expected_balance": expected_balance, "record_id": record_id})

            fixed_count += 1

        print(f"✓ Fixed {fixed_count} refund records")

        # 提交修复
        connection.commit()

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
