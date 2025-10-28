"""add_finance_tables

Revision ID: ebe1c24204e4
Revises: 002_add_site_description
Create Date: 2025-10-18 11:09:54.002155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = 'ebe1c24204e4'
down_revision: Union[str, None] = '002_add_site_description'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create finance_accounts and finance_operation_logs tables for US6 财务后台功能.

    NOTE: This migration is a no-op because finance_accounts and finance_operation_logs
    tables were already created in the initial migration (001_initial).
    The FK constraints were also already created in the initial migration.
    """
    # Tables already exist in 001_initial migration - no operation needed
    pass


def downgrade() -> None:
    """Remove finance tables and FK constraints."""
    # No operation needed - tables are managed by 001_initial migration
    pass
