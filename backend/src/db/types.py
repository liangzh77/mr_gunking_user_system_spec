"""Custom database types for cross-database compatibility.

Provides types that work across PostgreSQL and SQLite.
"""

import json
from uuid import UUID as PyUUID

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, UUID as PG_UUID


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses
    CHAR(36) storing as stringified hex values.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate type for the dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """Convert UUID to string for SQLite, keep as-is for PostgreSQL."""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, PyUUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        """Convert string back to UUID for SQLite, keep as-is for PostgreSQL."""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return PyUUID(value)
            return value


class JSON(TypeDecorator):
    """Platform-independent JSON type.

    Uses PostgreSQL's JSONB when available, otherwise uses
    TEXT storing as JSON strings.
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate type for the dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        """Convert dict/list to JSON string for SQLite, keep as-is for PostgreSQL."""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Convert JSON string back to dict/list for SQLite, keep as-is for PostgreSQL."""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, str):
                return json.loads(value)
            return value
