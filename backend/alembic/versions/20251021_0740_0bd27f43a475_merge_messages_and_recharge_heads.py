"""merge messages and recharge heads

Revision ID: 0bd27f43a475
Revises: 314ba7af94a7, a8f9c2d3e4b5
Create Date: 2025-10-21 07:40:54.549275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bd27f43a475'
down_revision: Union[str, None] = ('314ba7af94a7', 'a8f9c2d3e4b5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
