"""add_bank_transfer_to_payment_channel

Revision ID: ad756a9bce16
Revises: d9f8e7c6b5a4
Create Date: 2025-11-16 14:47:28.529726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad756a9bce16'
down_revision: Union[str, None] = 'd9f8e7c6b5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old constraint
    op.drop_constraint('chk_payment_channel', 'transaction_records', type_='check')

    # Create new constraint with 'bank_transfer' added
    op.create_check_constraint(
        'chk_payment_channel',
        'transaction_records',
        "payment_channel IS NULL OR payment_channel IN ('wechat', 'alipay', 'bank_transfer')"
    )


def downgrade() -> None:
    # Drop new constraint
    op.drop_constraint('chk_payment_channel', 'transaction_records', type_='check')

    # Restore old constraint
    op.create_check_constraint(
        'chk_payment_channel',
        'transaction_records',
        "payment_channel IS NULL OR payment_channel IN ('wechat', 'alipay')"
    )
