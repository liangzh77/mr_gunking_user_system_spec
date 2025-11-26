"""remove_application_price_per_player

Revision ID: 9bafb03b27d5
Revises: add_application_modes
Create Date: 2025-11-26 02:41:17.979174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bafb03b27d5'
down_revision: Union[str, None] = 'add_application_modes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """删除 applications 表的 price_per_player 字段及相关约束和索引"""
    # 1. 删除 CHECK 约束
    op.drop_constraint('chk_price_positive', 'applications', type_='check')

    # 2. 删除索引
    op.drop_index('idx_app_price', table_name='applications')

    # 3. 删除列
    op.drop_column('applications', 'price_per_player')


def downgrade() -> None:
    """恢复 applications 表的 price_per_player 字段及相关约束和索引"""
    # 1. 添加列
    op.add_column('applications',
        sa.Column('price_per_player', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00')
    )

    # 2. 创建索引
    op.create_index('idx_app_price', 'applications', ['price_per_player'])

    # 3. 创建 CHECK 约束
    op.create_check_constraint('chk_price_positive', 'applications', 'price_per_player > 0')

    # 4. 删除 server_default（只在创建列时需要）
    op.alter_column('applications', 'price_per_player', server_default=None)
