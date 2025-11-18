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
    # Drop the old constraint
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')

    # Update existing negative refund amounts to positive
    op.execute("""
        UPDATE transaction_records
        SET amount = ABS(amount)
        WHERE transaction_type = 'refund' AND amount < 0
    """)

    # Add the new constraint that supports positive refund amounts
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        """
        (transaction_type != 'refund' AND balance_after = balance_before + amount) OR
        (transaction_type = 'refund' AND balance_after = balance_before - amount)
        """
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint('chk_balance_calc', 'transaction_records', type_='check')

    # Restore the old constraint
    op.create_check_constraint(
        'chk_balance_calc',
        'transaction_records',
        'balance_after = balance_before + amount'
    )
