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
from .core.cache import init_cache, close_cache
from .core.metrics import prometheus  # Import to register metrics
# from .core.monitoring import initialize_monitoring_system, get_monitoring_status  # 临时禁用
# from .core.performance import initialize_performance_system, get_performance_status
# 临时禁用性能优化系统以避免导入问题
from .db import close_db, health_check, init_db
from .middleware import register_exception_handlers, SecurityHeadersMiddleware
from .schemas import HealthCheckResponse
# from .api.v1.monitoring.endpoints import router as monitoring_router  # 临时禁用

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

        # Create tables for both SQLite and PostgreSQL
        from .db.session import create_tables
        await create_tables()
        logger.info("database_tables_created")

        # Initialize Redis cache
        await init_cache()
        logger.info("redis_cache_initialized", redis_url=settings.REDIS_URL)

        # Ensure database partitions exist (create next 6 months)
        from .db.partition_manager import ensure_partitions
        await ensure_partitions(months_ahead=6)
        logger.info("database_partitions_ensured")

        # Initialize monitoring system
        monitoring_config = {
            'health_monitoring': {
                'database_url': settings.DATABASE_URL,
                'redis_url': settings.REDIS_URL,
                'monitoring_interval': 60,
                'disk_warning_threshold': 80.0,
                'disk_critical_threshold': 90.0,
                'memory_warning_threshold': 80.0,
                'memory_critical_threshold': 90.0
            },
            'alert_system': {
                'evaluation_interval': 60,
                'notification_channels': {
                    # 这里可以根据配置文件加载通知渠道
                },
                'alert_rules': [
                    {
                        'id': 'high_cpu_usage',
                        'name': 'CPU使用率过高',
                        'description': '系统CPU使用率超过阈值',
                        'severity': 'warning',
                        'condition': 'system.cpu.usage > 80',
                        'threshold': 80,
                        'consecutive_failures': 2,
                        'evaluation_interval': 60,
                        'notification_channels': ['email'],
                        'cooldown_period': 300
                    },
                    {
                        'id': 'high_memory_usage',
                        'name': '内存使用率过高',
                        'description': '系统内存使用率超过阈值',
                        'severity': 'critical',
                        'condition': 'system.memory.usage > 90',
                        'threshold': 90,
                        'consecutive_failures': 1,
                        'evaluation_interval': 60,
                        'notification_channels': ['email'],
                        'cooldown_period': 180
                    },
                    {
                        'id': 'database_connection_issue',
                        'name': '数据库连接问题',
                        'description': '数据库连接池使用率过高',
                        'severity': 'critical',
                        'condition': 'database.connection_pool_usage > 85',
                        'threshold': 85,
                        'consecutive_failures': 1,
                        'evaluation_interval': 30,
                        'notification_channels': ['email'],
                        'cooldown_period': 120
                    }
                ]
            }
        }

        # await initialize_monitoring_system(app, monitoring_config)
        # logger.info("monitoring_system_initialized", status=get_monitoring_status())

        # Initialize performance optimization system (临时禁用)
        # performance_config = {
        #     'cache': {
        #         'auto_warmup': False,  # 启动时不自动预热，避免影响启动速度
        #         'max_concurrent_warmers': 5,
        #         'local_cache_size': 1000,
        #         'redis_namespace': 'mr_performance'
        #     },
        #     'database': {
        #         'slow_query_threshold': 1.0,
        #         'max_stats_entries': 10000,
        #         'enable_startup_analysis': False
        #     },
        #     'api': {
        #         'enable_response_compression': True,
        #         'enable_smart_caching': True,
        #         'enable_request_batching': True,
        #         'enable_rate_limiting': True,
        #         'enable_deduplication': True,
        #         'max_concurrent_requests': 100,
        #         'default_cache_ttl': 300,
        #         'slow_request_threshold': 1.0,
        #         'add_middleware': True
        #     }
        # }

        # await initialize_performance_system(app, performance_config)
        # logger.info("performance_system_initialized", status=get_performance_status())

        # Start task scheduler
        from .tasks import start_scheduler
        await start_scheduler()
        logger.info("task_scheduler_started")

        # Application ready
        logger.info("application_ready")

    except Exception as e:
        logger.error("application_startup_failed", error=str(e), exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("application_shutdown_started")

    try:
        # Stop task scheduler
        from .tasks import stop_scheduler
        await stop_scheduler()
        logger.info("task_scheduler_stopped")
    except Exception as e:
        logger.error("task_scheduler_stop_failed", error=str(e), exc_info=True)

    try:
        # Close Redis cache
        await close_cache()
        logger.info("redis_cache_closed")
    except Exception as e:
        logger.error("redis_cache_close_failed", error=str(e), exc_info=True)

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

    # Add security headers middleware
    # Note: HTTPS redirect is handled by reverse proxy in production
    app.add_middleware(SecurityHeadersMiddleware)

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

        # Get performance system status (临时禁用)
        # performance_status = get_performance_status()
        # performance_healthy = not any(
        #     component.get('error') for component in performance_status.values()
        # )

        overall_healthy = db_healthy  # and performance_healthy

        return HealthCheckResponse(
            status="healthy" if overall_healthy else "unhealthy",
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

    # Monitoring routes (管理员权限) - 临时禁用
    # app.include_router(monitoring_router, prefix=f"{settings.API_V1_PREFIX}/monitoring", tags=["monitoring"])


# Create application instance
app = create_app()


# Log application info on import
if __name__ != "__main__":
    logger.info(
        "fastapi_app_created",
        app_title=app.title,
        app_version=app.version,
    )
