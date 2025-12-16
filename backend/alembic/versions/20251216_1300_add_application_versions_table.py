"""add_application_versions_table

Revision ID: add_app_versions_table
Revises: add_app_version_fields
Create Date: 2025-12-16 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_app_versions_table'
down_revision: Union[str, None] = 'add_app_version_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建应用版本历史表"""
    op.create_table(
        'application_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('application_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('applications.id', ondelete='CASCADE'),
                  nullable=False, comment='所属应用ID'),
        sa.Column('version', sa.String(32), nullable=False,
                  comment='版本号(如 1.0.3)'),
        sa.Column('filename', sa.String(256), nullable=False,
                  comment='原始文件名'),
        sa.Column('file_path', sa.String(512), nullable=False,
                  comment='七牛云存储路径'),
        sa.Column('apk_url', sa.String(512), nullable=False,
                  comment='APK下载链接'),
        sa.Column('file_size', sa.BigInteger, nullable=True,
                  comment='文件大小(字节)'),
        sa.Column('description', sa.Text, nullable=True,
                  comment='版本说明'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.func.current_timestamp(),
                  nullable=False, comment='上传时间'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('admin_accounts.id', ondelete='SET NULL'),
                  nullable=True, comment='上传者(管理员ID)'),
    )

    # 创建索引
    op.create_index('idx_app_version_app_id', 'application_versions',
                    ['application_id'])
    op.create_index('idx_app_version_version', 'application_versions',
                    ['version'])
    op.create_index('idx_app_version_created_at', 'application_versions',
                    ['created_at'])


def downgrade() -> None:
    """删除应用版本历史表"""
    op.drop_index('idx_app_version_created_at', 'application_versions')
    op.drop_index('idx_app_version_version', 'application_versions')
    op.drop_index('idx_app_version_app_id', 'application_versions')
    op.drop_table('application_versions')
