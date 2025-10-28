"""add_index_on_username_fields

Revision ID: 10567dfc9d13
Revises: ebe1c24204e4
Create Date: 2025-10-18 13:47:50.460422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10567dfc9d13'
down_revision: Union[str, None] = 'ebe1c24204e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 admin_accounts.username 添加索引
    op.create_index(
        'ix_admin_accounts_username',
        'admin_accounts',
        ['username'],
        unique=False
    )

    # 为 operator_accounts.username 添加索引
    op.create_index(
        'ix_operator_accounts_username',
        'operator_accounts',
        ['username'],
        unique=False
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_operator_accounts_username', table_name='operator_accounts')
    op.drop_index('ix_admin_accounts_username', table_name='admin_accounts')
