"""add protocol and headset fields

Revision ID: e8d7c6b5a4f3
Revises: f9a3b2c1d8e7
Create Date: 2025-11-01 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'e8d7c6b5a4f3'
down_revision: Union[str, None] = 'f9a3b2c1d8e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add protocol_scheme to applications and headset_ids to game_usage_records."""

    # Add protocol_scheme to applications table
    op.add_column(
        'applications',
        sa.Column('protocol_scheme', sa.String(50), nullable=True, comment='自定义协议名称，如 mrgun')
    )

    # Add headset_ids to usage_records table
    op.add_column(
        'usage_records',
        sa.Column('headset_ids', JSONB, nullable=True, comment='头显设备ID列表')
    )


def downgrade() -> None:
    """Remove protocol_scheme and headset_ids fields."""

    op.drop_column('usage_records', 'headset_ids')
    op.drop_column('applications', 'protocol_scheme')
