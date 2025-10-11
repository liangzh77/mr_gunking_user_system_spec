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
from ..models.admin import AdminAccount  # noqa: F401
