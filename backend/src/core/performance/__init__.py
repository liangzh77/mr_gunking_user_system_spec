"""
性能优化模块

集成缓存优化、数据库优化、批量操作等功能
"""
import structlog
from .cache_optimization import (
    CacheOptimizer,
    init_cache_optimization
)
from .database_optimization import (
    DatabaseOptimizer,
    init_database_optimization
)
from .api_optimization import (
    ApiOptimizer,
    init_api_optimization
)

logger = structlog.get_logger(__name__)


async def initialize_performance_system(app, config: dict):
    """
    初始化性能优化系统

    Args:
        app: FastAPI应用实例
        config: 性能优化配置
    """
    try:
        logger.info("initializing_performance_system")

        # 初始化缓存优化
        cache_optimizer = await init_cache_optimization(config.get('cache', {}))

        # 初始化数据库优化
        db_optimizer = await init_database_optimization(config.get('database', {}))

        # 初始化API优化
        api_optimizer = init_api_optimization(app, config.get('api', {}))

        logger.info("performance_system_initialization_completed",
                      cache_optimizer=cache_optimizer is not None,
                      db_optimizer=db_optimizer is not None,
                      api_optimizer=api_optimizer is not None)

    except Exception as e:
        logger.error("performance_system_initialization_failed", error=str(e))
        raise


def get_performance_status() -> dict:
    """
    获取性能优化系统状态

    Returns:
        性能优化系统状态信息
    """
    try:
        from ..cache.enhanced_cache import get_multi_cache
        from ..database.optimized_pool import get_db_pool
        from ..batch.optimizer import get_batch_manager

        cache = get_multi_cache()
        db_pool = get_db_pool()
        batch_manager = get_batch_manager()

        return {
            "cache_system": {
                "initialized": cache is not None,
                "stats": cache.get_stats() if cache else None
            },
            "database_pool": {
                "initialized": db_pool is not None,
                "status": db_pool.get_pool_status() if db_pool else None
            },
            "batch_manager": {
                "initialized": batch_manager is not None,
                "statistics": batch_manager.get_statistics() if batch_manager else None
            }
        }
    except Exception as e:
        logger.error("get_performance_status_error", error=str(e))
        return {"error": str(e)}


# 导出主要组件
__all__ = [
    'initialize_performance_system',
    'get_performance_status',
    'CacheOptimizer',
    'DatabaseOptimizer',
    'ApiOptimizer'
]