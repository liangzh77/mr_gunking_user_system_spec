"""
缓存模块

提供多级缓存、智能缓存策略等功能
"""

# 从老的cache模块导入兼容内容
from ..cache import RedisCache, get_cache, cache_result

# 尝试导入新的enhanced_cache模块
try:
    from .enhanced_cache import (
        get_multi_cache,
        get_cache_warmer,
        MultiLevelCache,
        CacheLevel,
        CachePolicy,
        LocalCache,
        RedisCache as EnhancedRedisCache,
        CacheWarmer,
        CacheStats
    )
except ImportError as e:
    import logging
    logging.warning(f"Failed to import enhanced_cache: {e}")
    # 提供空的占位符以避免导入错误
    get_multi_cache = None
    get_cache_warmer = None
    MultiLevelCache = None
    CacheLevel = None
    CachePolicy = None
    LocalCache = None
    EnhancedRedisCache = None
    CacheWarmer = None
    CacheStats = None

__all__ = [
    "RedisCache",
    "get_cache",
    "cache_result",
    "get_multi_cache",
    "get_cache_warmer",
    "MultiLevelCache",
    "CacheLevel",
    "CachePolicy",
    "LocalCache",
    "EnhancedRedisCache",
    "CacheWarmer",
    "CacheStats"
]