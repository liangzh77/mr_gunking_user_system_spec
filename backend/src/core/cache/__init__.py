"""
缓存模块

提供多级缓存、智能缓存策略等功能
"""

# 先尝试从老的cache模块导入兼容内容
try:
    from ..cache import RedisCache, get_cache, cache_result
    __all__ = ["RedisCache", "get_cache", "cache_result"]
except ImportError:
    pass

# 导入新的enhanced_cache模块
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

    __all__ += [
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
except ImportError as e:
    import logging
    logging.warning(f"Failed to import enhanced_cache: {e}")