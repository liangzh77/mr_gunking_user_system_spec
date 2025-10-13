"""Database module containing models, sessions, and utilities."""

from .base import Base
from .session import (
    close_db,
    get_db,
    get_db_context,
    get_db_session,
    get_engine,
    get_session_maker,
    health_check,
    init_db,
)

# Backward compatibility: allow `from src.db.session import engine`
# This is a function that returns the engine, not the engine itself
engine = get_engine

__all__ = [
    "Base",
    "init_db",
    "close_db",
    "get_engine",
    "get_session_maker",
    "get_db",
    "get_db_session",
    "get_db_context",
    "health_check",
    "engine",
]
