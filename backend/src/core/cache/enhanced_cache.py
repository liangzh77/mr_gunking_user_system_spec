"""
增强缓存系统

提供多层缓存、智能缓存策略、性能优化等功能
支持本地缓存 + Redis 分布式缓存的混合架构
"""
import asyncio
import json
import time
import hashlib
import logging
import pickle
import structlog
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict
from enum import Enum

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

try:
    from .cache import get_cache as get_base_cache
except ImportError:
    # 避免循环导入
    def get_base_cache():
        raise NotImplementedError("Base cache not available")
from ..metrics.enhanced_metrics import record_cache_operation

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class CacheLevel(Enum):
    """缓存级别"""
    L1_LOCAL = "l1_local"      # 本地内存缓存
    L2_REDIS = "l2_redis"      # Redis分布式缓存
    L3_DATABASE = "l3_database" # 数据库（作为缓存的最后级别）


class CachePolicy(Enum):
    """缓存策略"""
    LRU = "lru"                # 最近最少使用
    LFU = "lfu"                # 最少使用频率
    FIFO = "fifo"              # 先进先出
    TTL = "ttl"                # 基于时间过期


class CacheStats:
    """缓存统计信息"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.start_time = time.time()

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def operations_per_second(self) -> float:
        """每秒操作数"""
        elapsed = time.time() - self.start_time
        total_ops = self.hits + self.misses + self.sets + self.deletes
        return total_ops / elapsed if elapsed > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'errors': self.errors,
            'hit_rate': self.hit_rate,
            'operations_per_second': self.operations_per_second,
            'uptime_seconds': time.time() - self.start_time
        }


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0

    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """获取年龄（秒）"""
        return time.time() - self.created_at


class LocalCache:
    """本地内存缓存实现"""

    def __init__(self, max_size: int = 1000, policy: CachePolicy = CachePolicy.LRU):
        self.max_size = max_size
        self.policy = policy
        self._cache: Dict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = asyncio.Lock()

    def _evict_if_needed(self):
        """根据策略淘汰缓存项"""
        if len(self._cache) <= self.max_size:
            return

        if self.policy == CachePolicy.LRU:
            # LRU: 移除最久未访问的项
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        elif self.policy == CachePolicy.FIFO:
            # FIFO: 移除最早插入的项
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        elif self.policy == CachePolicy.TTL:
            # TTL: 移除已过期的项
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]

            # 如果没有过期的项，仍然移除最旧的
            if len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                record_cache_operation("get", "local", "miss")
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats.misses += 1
                record_cache_operation("get", "local", "miss")
                return None

            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = time.time()

            # LRU策略：移动到末尾
            if self.policy == CachePolicy.LRU:
                self._cache.move_to_end(key)

            self._stats.hits += 1
            record_cache_operation("get", "local", "hit")
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            async with self._lock:
                # 计算大小（粗略估计）
                size_bytes = len(pickle.dumps(value))

                expires_at = None
                if ttl:
                    expires_at = time.time() + ttl

                entry = CacheEntry(
                    value=value,
                    expires_at=expires_at,
                    size_bytes=size_bytes
                )

                # 淘汰旧项
                self._evict_if_needed()

                # 添加新项
                self._cache[key] = entry
                self._stats.sets += 1
                record_cache_operation("set", "local", "success")
                return True

        except Exception as e:
            self._stats.errors += 1
            record_cache_operation("set", "local", "error")
            logger.error("local_cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1
                record_cache_operation("delete", "local", "success")
                return True
            return False

    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            record_cache_operation("clear", "local", "success")

    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        return self._stats

    def get_size_info(self) -> Dict[str, Any]:
        """获取大小信息"""
        total_size = sum(entry.size_bytes for entry in self._cache.values())
        return {
            'items_count': len(self._cache),
            'max_size': self.max_size,
            'total_size_bytes': total_size,
            'utilization_rate': len(self._cache) / self.max_size,
            'average_item_size': total_size / len(self._cache) if self._cache else 0
        }


class EnhancedRedisCache:
    """增强的Redis缓存"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._stats = CacheStats()

    def _make_key(self, key: str, namespace: Optional[str] = None) -> str:
        """生成完整的缓存键"""
        if namespace:
            return f"{namespace}:{key}"
        return key

    async def get(self, key: str, namespace: Optional[str] = None) -> Optional[Any]:
        """获取缓存值"""
        try:
            full_key = self._make_key(key, namespace)
            value = await self.redis.get(full_key)

            if value is None:
                self._stats.misses += 1
                record_cache_operation("get", "redis", "miss")
                return None

            # 尝试JSON反序列化
            try:
                result = json.loads(value)
                self._stats.hits += 1
                record_cache_operation("get", "redis", "hit")
                return result
            except json.JSONDecodeError:
                # 如果不是JSON，尝试pickle
                try:
                    result = pickle.loads(value)
                    self._stats.hits += 1
                    record_cache_operation("get", "redis", "hit")
                    return result
                except pickle.PickleError:
                    logger.warning("failed_to_deserialize_cache_value", key=full_key)
                    self._stats.misses += 1
                    return None

        except Exception as e:
            self._stats.errors += 1
            record_cache_operation("get", "redis", "error")
            logger.error("redis_cache_get_error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None,
                 namespace: Optional[str] = None, serialize_method: str = "json") -> bool:
        """设置缓存值"""
        try:
            full_key = self._make_key(key, namespace)

            # 序列化
            if serialize_method == "json":
                serialized = json.dumps(value, default=str)
            elif serialize_method == "pickle":
                serialized = pickle.dumps(value)
            else:
                raise ValueError(f"Unsupported serialize method: {serialize_method}")

            # 设置到Redis
            if ttl:
                await self.redis.setex(full_key, ttl, serialized)
            else:
                await self.redis.set(full_key, serialized)

            self._stats.sets += 1
            record_cache_operation("set", "redis", "success")
            return True

        except Exception as e:
            self._stats.errors += 1
            record_cache_operation("set", "redis", "error")
            logger.error("redis_cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """删除缓存值"""
        try:
            full_key = self._make_key(key, namespace)
            result = await self.redis.delete(full_key)

            if result > 0:
                self._stats.deletes += 1
                record_cache_operation("delete", "redis", "success")
                return True
            return False

        except Exception as e:
            self._stats.errors += 1
            record_cache_operation("delete", "redis", "error")
            logger.error("redis_cache_delete_error", key=key, error=str(e))
            return False

    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """检查键是否存在"""
        try:
            full_key = self._make_key(key, namespace)
            return await self.redis.exists(full_key) > 0
        except Exception as e:
            logger.error("redis_cache_exists_error", key=key, error=str(e))
            return False

    async def ttl(self, key: str, namespace: Optional[str] = None) -> Optional[int]:
        """获取剩余TTL"""
        try:
            full_key = self._make_key(key, namespace)
            return await self.redis.ttl(full_key)
        except Exception as e:
            logger.error("redis_cache_ttl_error", key=key, error=str(e))
            return None

    async def delete_pattern(self, pattern: str, namespace: Optional[str] = None) -> int:
        """删除匹配模式的所有键"""
        try:
            full_pattern = self._make_key(pattern, namespace)
            keys = []
            async for key in self.redis.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                return await self.redis.delete(*keys)
            return 0

        except Exception as e:
            self._stats.errors += 1
            record_cache_operation("delete_pattern", "redis", "error")
            logger.error("redis_cache_delete_pattern_error", pattern=pattern, error=str(e))
            return 0

    def get_stats(self) -> CacheStats:
        """获取统计信息"""
        return self._stats


class MultiLevelCache:
    """多层缓存系统"""

    def __init__(self,
                 local_cache_size: int = 1000,
                 local_policy: CachePolicy = CachePolicy.LRU,
                 redis_namespace: str = "mr_cache"):
        self.local_cache = LocalCache(local_cache_size, local_policy)
        self.redis_cache = None  # 将在init中设置
        self.redis_namespace = redis_namespace
        self._global_stats = CacheStats()

    async def initialize(self):
        """初始化Redis缓存"""
        try:
            base_cache = get_base_cache()
            if base_cache._client:
                self.redis_cache = EnhancedRedisCache(base_cache._client)
                logger.info("multi_level_cache_initialized",
                           local_size=self.local_cache.max_size,
                           redis_namespace=self.redis_namespace)
            else:
                logger.warning("redis_not_available_for_multi_cache")
        except Exception as e:
            logger.error("multi_level_cache_init_error", error=str(e))

    async def get(self, key: str, use_redis: bool = True) -> Optional[Any]:
        """获取缓存值（多层查找）"""
        start_time = time.time()

        # L1: 本地缓存
        value = await self.local_cache.get(key)
        if value is not None:
            self._global_stats.hits += 1
            record_cache_operation("get", "multilevel", "l1_hit")
            return value

        # L2: Redis缓存
        if use_redis and self.redis_cache:
            value = await self.redis_cache.get(key, self.redis_namespace)
            if value is not None:
                # 回填到本地缓存
                await self.local_cache.set(key, value, ttl=300)  # 5分钟本地缓存
                self._global_stats.hits += 1
                record_cache_operation("get", "multilevel", "l2_hit")
                return value

        # 缓存未命中
        self._global_stats.misses += 1
        record_cache_operation("get", "multilevel", "miss")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None,
                 local_ttl: Optional[int] = None, use_redis: bool = True) -> bool:
        """设置缓存值（多层存储）"""
        success = True

        # L1: 本地缓存
        local_ttl = local_ttl or min(ttl or 3600, 300)  # 本地缓存最多5分钟
        local_success = await self.local_cache.set(key, value, ttl=local_ttl)
        success &= local_success

        # L2: Redis缓存
        if use_redis and self.redis_cache:
            redis_success = await self.redis_cache.set(
                key, value, ttl=ttl, namespace=self.redis_namespace
            )
            success &= redis_success

        if success:
            self._global_stats.sets += 1
            record_cache_operation("set", "multilevel", "success")
        else:
            self._global_stats.errors += 1
            record_cache_operation("set", "multilevel", "error")

        return success

    async def delete(self, key: str, use_redis: bool = True) -> bool:
        """删除缓存值（多层删除）"""
        success = True

        # L1: 本地缓存
        local_success = await self.local_cache.delete(key)
        success &= local_success

        # L2: Redis缓存
        if use_redis and self.redis_cache:
            redis_success = await self.redis_cache.delete(key, self.redis_namespace)
            success &= redis_success

        if success:
            self._global_stats.deletes += 1
            record_cache_operation("delete", "multilevel", "success")

        return success

    async def clear_local(self):
        """清空本地缓存"""
        await self.local_cache.clear()
        record_cache_operation("clear_local", "multilevel", "success")

    async def invalidate_pattern(self, pattern: str, use_redis: bool = True):
        """使匹配模式的缓存失效"""
        # 清空本地缓存中匹配的项
        if pattern == "*":
            await self.local_cache.clear()
        else:
            # 简单的模式匹配（实际应用中可能需要更复杂的匹配逻辑）
            local_keys = list(self.local_cache._cache.keys())
            for key in local_keys:
                if pattern.replace("*", "") in key:
                    await self.local_cache.delete(key)

        # 清空Redis中匹配的项
        if use_redis and self.redis_cache:
            deleted_count = await self.redis_cache.delete_pattern(pattern, self.redis_namespace)
            logger.info("cache_pattern_invalidated",
                       pattern=pattern,
                       deleted_count=deleted_count)

    def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存的统计信息"""
        return {
            'global': self._global_stats.to_dict(),
            'local_cache': {
                'stats': self.local_cache.get_stats().to_dict(),
                'size_info': self.local_cache.get_size_info()
            },
            'redis_cache': {
                'stats': self.redis_cache.get_stats().to_dict() if self.redis_cache else None
            }
        }


class CacheWarmer:
    """缓存预热器"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self._warming_tasks: List[asyncio.Task] = []

    async def warm_cache(self, warmers: Dict[str, Callable], max_concurrent: int = 10):
        """预热缓存"""
        logger.info("cache_warming_started", warmers_count=len(warmers))

        semaphore = asyncio.Semaphore(max_concurrent)

        async def warm_single(name: str, warmer_func: Callable):
            async with semaphore:
                try:
                    start_time = time.time()
                    result = await warmer_func()

                    if result is not None:
                        # 存储到缓存
                        await self.cache.set(f"warm:{name}", result, ttl=3600)

                        duration = time.time() - start_time
                        logger.info("cache_warmer_completed",
                                   name=name,
                                   duration_seconds=duration,
                                   success=True)
                    else:
                        logger.warning("cache_warmer_no_result", name=name)

                except Exception as e:
                    logger.error("cache_warmer_failed", name=name, error=str(e))

        # 创建预热任务
        tasks = [
            asyncio.create_task(warm_single(name, warmer))
            for name, warmer in warmers.items()
        ]

        # 等待所有任务完成
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("cache_warming_completed", total_tasks=len(tasks))

    async def warm_async(self, warmers: Dict[str, Callable]):
        """异步预热缓存（不阻塞）"""
        task = asyncio.create_task(self.warm_cache(warmers))
        self._warming_tasks.append(task)

        # 清理已完成的任务
        self._warming_tasks = [t for t in self._warming_tasks if not t.done()]

    async def cancel_all(self):
        """取消所有预热任务"""
        for task in self._warming_tasks:
            task.cancel()

        await asyncio.gather(*self._warming_tasks, return_exceptions=True)
        self._warming_tasks.clear()


# 全局多层缓存实例
_multi_cache: Optional[MultiLevelCache] = None
_cache_warmer: Optional[CacheWarmer] = None


def get_multi_cache() -> MultiLevelCache:
    """获取全局多层缓存实例"""
    global _multi_cache
    if _multi_cache is None:
        _multi_cache = MultiLevelCache(
            local_cache_size=1000,
            local_policy=CachePolicy.LRU,
            redis_namespace="mr_cache"
        )
    return _multi_cache


def get_cache_warmer() -> CacheWarmer:
    """获取缓存预热器实例"""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer(get_multi_cache())
    return _cache_warmer


async def init_enhanced_cache():
    """初始化增强缓存系统"""
    cache = get_multi_cache()
    await cache.initialize()
    logger.info("enhanced_cache_system_initialized")


def smart_cache(
    key_prefix: str,
    ttl: int = 300,
    local_ttl: Optional[int] = None,
    use_redis: bool = True,
    key_builder: Optional[Callable] = None,
    condition: Optional[Callable[[Any], bool]] = None
):
    """智能缓存装饰器

    Args:
        key_prefix: 缓存键前缀
        ttl: Redis缓存TTL（秒）
        local_ttl: 本地缓存TTL（秒）
        use_redis: 是否使用Redis缓存
        key_builder: 自定义键构建函数
        condition: 缓存条件函数，返回True时才缓存
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_multi_cache()

            # 构建缓存键
            if key_builder:
                cache_key = key_builder(func.__name__, *args, **kwargs)
            else:
                # 默认键构建策略
                key_parts = [key_prefix, func.__name__]

                # 添加位置参数
                if args:
                    key_parts.append(str(args[0]))

                # 添加关键字参数（排序后保证一致性）
                if kwargs:
                    sorted_kwargs = sorted(kwargs.items())
                    key_parts.extend(f"{k}={v}" for k, v in sorted_kwargs)

                cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            cached_value = await cache.get(cache_key, use_redis=use_redis)
            if cached_value is not None:
                logger.debug("smart_cache_hit", key=cache_key, function=func.__name__)
                return cached_value

            # 缓存未命中，执行函数
            logger.debug("smart_cache_miss", key=cache_key, function=func.__name__)
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 检查缓存条件
            if condition and not condition(result):
                logger.debug("smart_cache_condition_failed", key=cache_key)
                return result

            # 存储到缓存
            await cache.set(
                cache_key,
                result,
                ttl=ttl,
                local_ttl=local_ttl,
                use_redis=use_redis
            )

            logger.debug("smart_cache_set",
                       key=cache_key,
                       ttl=ttl,
                       execution_time_seconds=execution_time)

            return result

        return wrapper
    return decorator


def cache_with_fallback(
    key_prefix: str,
    ttl: int = 300,
    fallback_ttl: int = 60,
    fallback_value: Any = None
):
    """带回退值的缓存装饰器

    当缓存失效或出错时，返回预定义的回退值
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_multi_cache()

            # 构建缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args[0]) if args else 'default'}"

            try:
                # 尝试从缓存获取
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # 执行函数
                result = await func(*args, **kwargs)

                # 存储到缓存
                await cache.set(cache_key, result, ttl=ttl)
                return result

            except Exception as e:
                logger.error("cache_with_fallback_error",
                           key=cache_key,
                           error=str(e))

                # 尝试获取可能存在的缓存值
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # 返回回退值
                if fallback_value is not None:
                    await cache.set(cache_key, fallback_value, ttl=fallback_ttl)
                    return fallback_value

                raise

        return wrapper
    return decorator


# 便捷函数
async def get_cached_data(key: str, fetch_func: Callable, ttl: int = 300) -> Any:
    """获取缓存数据的便捷函数"""
    cache = get_multi_cache()

    # 尝试从缓存获取
    cached_value = await cache.get(key)
    if cached_value is not None:
        return cached_value

    # 执行获取函数
    result = await fetch_func()

    # 存储到缓存
    await cache.set(key, result, ttl=ttl)

    return result


async def invalidate_cache_pattern(pattern: str):
    """使匹配模式的缓存失效"""
    cache = get_multi_cache()
    await cache.invalidate_pattern(pattern)


async def get_cache_performance_report() -> Dict[str, Any]:
    """获取缓存性能报告"""
    cache = get_multi_cache()
    stats = cache.get_stats()

    return {
        'cache_performance': stats,
        'recommendations': _generate_cache_recommendations(stats),
        'timestamp': datetime.now().isoformat()
    }


def _generate_cache_recommendations(stats: Dict[str, Any]) -> List[str]:
    """生成缓存优化建议"""
    recommendations = []

    # 分析命中率
    global_hit_rate = stats['global']['hit_rate']
    if global_hit_rate < 0.7:
        recommendations.append(
            f"全局缓存命中率较低({global_hit_rate:.2%})，建议检查缓存策略或增加缓存时间"
        )

    # 分析本地缓存
    local_stats = stats['local_cache']['stats']
    if local_stats['hit_rate'] < 0.6:
        recommendations.append(
            f"本地缓存命中率较低({local_stats['hit_rate']:.2%})，建议增加本地缓存大小"
        )

    # 分析缓存大小
    local_size_info = stats['local_cache']['size_info']
    if local_size_info['utilization_rate'] > 0.9:
        recommendations.append(
            f"本地缓存利用率过高({local_size_info['utilization_rate']:.2%})，建议增加缓存大小"
        )

    # 分析错误率
    total_ops = (local_stats['hits'] + local_stats['misses'] +
                 local_stats['sets'] + local_stats['deletes'])
    if total_ops > 0:
        error_rate = local_stats['errors'] / total_ops
        if error_rate > 0.01:
            recommendations.append(
                f"缓存错误率较高({error_rate:.2%})，建议检查缓存配置和网络连接"
            )

    return recommendations