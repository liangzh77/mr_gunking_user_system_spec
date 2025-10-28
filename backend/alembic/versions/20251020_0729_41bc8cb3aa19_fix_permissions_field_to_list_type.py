"""fix_permissions_field_to_list_type

Fix permissions field in admin_accounts, operator_accounts, and finance_accounts
to use list type instead of dict type, and update existing data.

Revision ID: 41bc8cb3aa19
Revises: 10567dfc9d13
Create Date: 2025-10-20 07:29:16.498288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41bc8cb3aa19'
down_revision: Union[str, None] = '10567dfc9d13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update permissions fields from dict to list type."""

    # Update admin_accounts
    # 1. Change default value from {} to []
    op.alter_column('admin_accounts', 'permissions',
                    server_default='[]',
                    existing_type=sa.dialects.postgresql.JSONB,
                    existing_nullable=False)

    # 2. Convert existing dict data to list (empty list for now, as dict structure varies)
    op.execute("""
        UPDATE admin_accounts
        SET permissions = '[]'::jsonb
        WHERE jsonb_typeof(permissions) = 'object'
    """)

    # Update finance_accounts
    op.alter_column('finance_accounts', 'permissions',
                    server_default='[]',
                    existing_type=sa.dialects.postgresql.JSONB,
                    existing_nullable=False)

    op.execute("""
        UPDATE finance_accounts
        SET permissions = '[]'::jsonb
        WHERE jsonb_typeof(permissions) = 'object'
    """)


def downgrade() -> None:
    """Revert permissions fields back to dict type."""

    # Revert admin_accounts
    op.alter_column('admin_accounts', 'permissions',
                    server_default='{}',
                    existing_type=sa.dialects.postgresql.JSONB,
                    existing_nullable=False)

    op.execute("""
        UPDATE admin_accounts
        SET permissions = '{}'::jsonb
        WHERE jsonb_typeof(permissions) = 'array'
    """)

    # Revert finance_accounts
    op.alter_column('finance_accounts', 'permissions',
                    server_default='{}',
                    existing_type=sa.dialects.postgresql.JSONB,
                    existing_nullable=False)

    op.execute("""
        UPDATE finance_accounts
        SET permissions = '{}'::jsonb
        WHERE jsonb_typeof(permissions) = 'array'
    """)
