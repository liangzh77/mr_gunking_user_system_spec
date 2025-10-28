"""Add description field to operation_sites table

Revision ID: 002_add_site_description
Revises: 001_initial
Create Date: 2025-10-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_site_description'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add description column to operation_sites table.

    This field was defined in the OpenAPI contract but missed in the initial
    migration. Adding it to align with the API specification.
    """
    op.add_column(
        'operation_sites',
        sa.Column('description', sa.Text(), nullable=True, comment='运营点描述')
    )


def downgrade() -> None:
    """Remove description column from operation_sites table."""
    op.drop_column('operation_sites', 'description')
