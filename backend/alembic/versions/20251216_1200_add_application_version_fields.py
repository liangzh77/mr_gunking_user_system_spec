"""add_application_version_fields

Revision ID: add_app_version_fields
Revises: 9bafb03b27d5
Create Date: 2025-12-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_app_version_fields'
down_revision: Union[str, None] = '9bafb03b27d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加应用版本管理字段"""
    # 添加 latest_version 字段
    op.add_column('applications',
        sa.Column('latest_version', sa.String(32), nullable=True,
                  comment='最新版本号(如 1.0.3)'))

    # 添加 apk_url 字段
    op.add_column('applications',
        sa.Column('apk_url', sa.String(512), nullable=True,
                  comment='APK下载链接(七牛云存储)'))


def downgrade() -> None:
    """移除应用版本管理字段"""
    op.drop_column('applications', 'apk_url')
    op.drop_column('applications', 'latest_version')
