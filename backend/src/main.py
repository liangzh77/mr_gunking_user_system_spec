"""FastAPI application entry point.

This module initializes the FastAPI application with all middleware,
routers, and lifecycle event handlers.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .core import configure_logging, get_logger, get_settings
from .core.metrics import prometheus  # Import to register metrics
from .db import close_db, health_check, init_db
from .middleware import register_exception_handlers
from .schemas import HealthCheckResponse

# Configure logging before app initialization
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown tasks:
    - Startup: Initialize database, logging
    - Shutdown: Close database connections

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    settings = get_settings()

    # Startup
    logger.info(
        "application_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    try:
        # Initialize database
        init_db()
        logger.info("database_initialized", database_url=settings.DATABASE_URL)

        # Create tables if using SQLite
        if settings.DATABASE_URL.startswith("sqlite"):
            from .db.session import create_tables
            await create_tables()
            logger.info("database_tables_created")

        # Application ready
        logger.info("application_ready")

    except Exception as e:
        logger.error("application_startup_failed", error=str(e), exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("application_shutdown_started")

    try:
        await close_db()
        logger.info("database_closed")
    except Exception as e:
        logger.error("database_close_failed", error=str(e), exc_info=True)

    logger.info("application_shutdown_completed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="MR游戏运营管理系统 - 后端API",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Register routes
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """Register all API routes.

    Args:
        app: FastAPI application instance
    """
    settings = get_settings()

    # Health check endpoint
    @app.get(
        "/health",
        response_model=HealthCheckResponse,
        tags=["Health"],
        summary="Health Check",
        description="Check application and database health status",
    )
    async def health_check_endpoint() -> HealthCheckResponse:
        """Health check endpoint.

        Returns:
            HealthCheckResponse: Application health status
        """
        db_healthy = await health_check()

        return HealthCheckResponse(
            status="healthy" if db_healthy else "unhealthy",
            database=db_healthy,
            version=settings.APP_VERSION,
            timestamp=datetime.now(),
        )

    # Root endpoint
    @app.get(
        "/",
        tags=["Root"],
        summary="API Root",
        description="Get API information",
    )
    async def root() -> dict[str, str]:
        """Root endpoint providing API information.

        Returns:
            dict: API metadata
        """
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs_url": "/api/docs" if not settings.is_production else "disabled",
        }

    # Prometheus metrics endpoint
    @app.get(
        "/metrics",
        tags=["Monitoring"],
        summary="Prometheus Metrics",
        description="Export Prometheus metrics for monitoring",
        include_in_schema=not settings.is_production
    )
    async def metrics() -> Response:
        """Prometheus metrics endpoint.

        Returns:
            Response: Prometheus metrics in text format
        """
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    # API v1 routes
    from .api.v1 import api_router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Create application instance
app = create_app()


# Log application info on import
if __name__ != "__main__":
    logger.info(
        "fastapi_app_created",
        app_title=app.title,
        app_version=app.version,
    )
