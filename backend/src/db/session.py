"""Database session management for async SQLAlchemy.

This module provides the async engine, sessionmaker, and dependency injection
for database sessions in FastAPI endpoints.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..core.config import get_settings

# Global engine instance (initialized on app startup)
_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get the global async engine instance.

    Returns:
        AsyncEngine: SQLAlchemy async engine

    Raises:
        RuntimeError: If engine is not initialized

    Example:
        >>> engine = get_engine()
        >>> async with engine.begin() as conn:
        ...     await conn.execute(...)
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_db() first."
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get the global async session maker.

    Returns:
        async_sessionmaker[AsyncSession]: Configured session factory

    Raises:
        RuntimeError: If session maker is not initialized
    """
    if _async_session_maker is None:
        raise RuntimeError(
            "Database session maker not initialized. Call init_db() first."
        )
    return _async_session_maker


def init_db() -> None:
    """Initialize database engine and session maker.

    This should be called once during application startup.
    Reads database URL and pool settings from application config.

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> @app.on_event("startup")
        ... async def startup():
        ...     init_db()
    """
    global _engine, _async_session_maker

    settings = get_settings()

    # Create async engine with connection pooling
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # Log SQL queries in debug mode
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create session maker
    _async_session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Allow access to objects after commit
        autoflush=False,  # Manual flush control
        autocommit=False,  # Explicit transaction management
    )


async def close_db() -> None:
    """Close database engine and dispose of connection pool.

    This should be called once during application shutdown.

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> @app.on_event("shutdown")
        ... async def shutdown():
        ...     await close_db()
    """
    global _engine, _async_session_maker

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function for FastAPI to inject database sessions.

    Yields an async session that is automatically closed after use.
    Handles transaction rollback on exceptions.

    Usage in FastAPI endpoint:
        >>> from fastapi import Depends
        >>> @app.get("/users")
        ... async def get_users(db: AsyncSession = Depends(get_db_session)):
        ...     result = await db.execute(select(User))
        ...     return result.scalars().all()

    Yields:
        AsyncSession: Database session for the request

    Example:
        >>> async for session in get_db_session():
        ...     result = await session.execute(select(User))
        ...     users = result.scalars().all()
    """
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI.

    Useful for background tasks, CLI scripts, or testing.

    Usage:
        >>> async with get_db_context() as session:
        ...     result = await session.execute(select(User))
        ...     users = result.scalars().all()

    Yields:
        AsyncSession: Database session
    """
    session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def health_check() -> bool:
    """Check database connectivity.

    Returns:
        bool: True if database is accessible, False otherwise

    Example:
        >>> is_healthy = await health_check()
        >>> if is_healthy:
        ...     print("Database is healthy")
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
