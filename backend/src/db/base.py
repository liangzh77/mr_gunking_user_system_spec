"""SQLAlchemy Base class and metadata for all models.

This module defines the declarative base that all ORM models inherit from.
Models should be imported in alembic/env.py for migration discovery, not here,
to avoid circular imports.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    All models should inherit from this class to be discovered by Alembic
    and participate in the ORM system.
    """
    pass
