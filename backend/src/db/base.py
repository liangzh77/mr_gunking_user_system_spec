"""SQLAlchemy Base class and metadata for all models.

This module defines the declarative base that all ORM models inherit from.
Import all models here to ensure Alembic can discover them during migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    All models should inherit from this class to be discovered by Alembic
    and participate in the ORM system.
    """
    pass


# Import all models here for Alembic discovery
# User Story 1 - 游戏授权与实时计费
from ..models.admin import AdminAccount  # noqa: F401
from ..models.operator import OperatorAccount  # noqa: F401
from ..models.application import Application  # noqa: F401
from ..models.site import OperationSite  # noqa: F401
from ..models.usage_record import UsageRecord  # noqa: F401
from ..models.transaction import TransactionRecord  # noqa: F401
from ..models.authorization import OperatorAppAuthorization  # noqa: F401
