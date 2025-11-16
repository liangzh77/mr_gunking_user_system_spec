"""rename protocol_scheme to launch_exe_path

Revision ID: c6eb37ef2991
Revises: e8d7c6b5a4f3
Create Date: 2025-11-02 15:12:03.211026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6eb37ef2991'
down_revision: Union[str, None] = 'e8d7c6b5a4f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add launch_exe_path column if it doesn't exist."""
    # Check if column exists and add it if needed
    from sqlalchemy import inspect
    from alembic import context

    conn = context.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('applications')]

    # If launch_exe_path already exists, do nothing
    if 'launch_exe_path' in columns:
        return

    # If protocol_scheme exists, rename it
    if 'protocol_scheme' in columns:
        op.alter_column(
            'applications',
            'protocol_scheme',
            new_column_name='launch_exe_path',
            type_=sa.String(500),
            comment='启动exe的绝对路径，如 C:\\Program Files\\MRGaming\\HeadsetServer.exe'
        )
    else:
        # Otherwise, add the new column
        op.add_column(
            'applications',
            sa.Column('launch_exe_path', sa.String(500), nullable=True,
                     comment='启动exe的绝对路径，如 C:\\Program Files\\MRGaming\\HeadsetServer.exe')
        )


def downgrade() -> None:
    """Rename launch_exe_path back to protocol_scheme and restore length."""
    # Rename column back and change type
    op.alter_column(
        'applications',
        'launch_exe_path',
        new_column_name='protocol_scheme',
        type_=sa.String(50),
        comment='自定义协议名称，如 mrgun'
    )
