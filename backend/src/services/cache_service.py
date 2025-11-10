"""缓存服务 - 为游戏授权接口提供Redis缓存

优化目标:
- 减少数据库查询次数 (3次 → 1次 或 0次)
- 降低平均响应延迟 (579ms → 100-150ms)
- 提升系统吞吐量

缓存策略:
- 应用信息: TTL 30分钟 (变化频率低)
- 授权关系: TTL 10分钟 (变化频率中)
- 运营点信息: TTL 30分钟 (变化频率低)
- 运营商余额: 不缓存 (实时变化)
"""

import json
from typing import Optional, Any
from uuid import UUID
from decimal import Decimal

from ..core.cache import RedisCache
from ..core import get_logger

logger = get_logger(__name__)


class CacheService:
    """缓存服务 - 统一管理Redis缓存"""

    def __init__(self, redis_cache: RedisCache):
        """初始化缓存服务

        Args:
            redis_cache: Redis缓存客户端
        """
        self.redis = redis_cache

    # ========== 应用信息缓存 ==========

    async def get_application_by_code(self, app_code: str) -> Optional[dict]:
        """从缓存获取应用信息

        Args:
            app_code: 应用代码

        Returns:
            Optional[dict]: 应用信息字典,不存在则返回None
        """
        cache_key = f"app:{app_code}"
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(cached_data)
            logger.debug(f"Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error for {cache_key}: {e}")
            return None

    async def set_application(self, app_code: str, app_data: dict, ttl: int = 1800) -> None:
        """缓存应用信息

        Args:
            app_code: 应用代码
            app_data: 应用数据字典
            ttl: 过期时间(秒), 默认30分钟
        """
        cache_key = f"app:{app_code}"
        try:
            await self.redis.set(cache_key, json.dumps(app_data, default=str), ttl=ttl)
            logger.debug(f"Cache SET: {cache_key} (TTL={ttl}s)")
        except Exception as e:
            logger.error(f"Redis set error for {cache_key}: {e}")

    async def delete_application(self, app_code: str) -> None:
        """删除应用缓存 (管理员修改应用时调用)

        Args:
            app_code: 应用代码
        """
        cache_key = f"app:{app_code}"
        try:
            await self.redis.delete(cache_key)
            logger.info(f"Cache DELETE: {cache_key}")
        except Exception as e:
            logger.error(f"Redis delete error for {cache_key}: {e}")

    # ========== 授权关系缓存 ==========

    async def get_authorization(self, operator_id: UUID, app_code: str) -> Optional[dict]:
        """从缓存获取授权关系

        Args:
            operator_id: 运营商ID
            app_code: 应用代码

        Returns:
            Optional[dict]: 授权信息字典,不存在则返回None
        """
        cache_key = f"auth:{operator_id}:{app_code}"
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(cached_data)
            logger.debug(f"Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error for {cache_key}: {e}")
            return None

    async def set_authorization(
        self, operator_id: UUID, app_code: str, auth_data: dict, ttl: int = 600
    ) -> None:
        """缓存授权关系

        Args:
            operator_id: 运营商ID
            app_code: 应用代码
            auth_data: 授权数据字典
            ttl: 过期时间(秒), 默认10分钟
        """
        cache_key = f"auth:{operator_id}:{app_code}"
        try:
            await self.redis.set(cache_key, json.dumps(auth_data, default=str), ttl=ttl)
            logger.debug(f"Cache SET: {cache_key} (TTL={ttl}s)")
        except Exception as e:
            logger.error(f"Redis set error for {cache_key}: {e}")

    async def delete_authorization(self, operator_id: UUID, app_code: str) -> None:
        """删除授权缓存 (管理员修改授权时调用)

        Args:
            operator_id: 运营商ID
            app_code: 应用代码
        """
        cache_key = f"auth:{operator_id}:{app_code}"
        try:
            await self.redis.delete(cache_key)
            logger.info(f"Cache DELETE: {cache_key}")
        except Exception as e:
            logger.error(f"Redis delete error for {cache_key}: {e}")

    # ========== 运营点缓存 ==========

    async def get_site(self, site_id: UUID) -> Optional[dict]:
        """从缓存获取运营点信息

        Args:
            site_id: 运营点ID

        Returns:
            Optional[dict]: 运营点信息字典,不存在则返回None
        """
        cache_key = f"site:{site_id}"
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(cached_data)
            logger.debug(f"Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error for {cache_key}: {e}")
            return None

    async def set_site(self, site_id: UUID, site_data: dict, ttl: int = 1800) -> None:
        """缓存运营点信息

        Args:
            site_id: 运营点ID
            site_data: 运营点数据字典
            ttl: 过期时间(秒), 默认30分钟
        """
        cache_key = f"site:{site_id}"
        try:
            await self.redis.set(cache_key, json.dumps(site_data, default=str), ttl=ttl)
            logger.debug(f"Cache SET: {cache_key} (TTL={ttl}s)")
        except Exception as e:
            logger.error(f"Redis set error for {cache_key}: {e}")

    async def delete_site(self, site_id: UUID) -> None:
        """删除运营点缓存 (运营商修改运营点时调用)

        Args:
            site_id: 运营点ID
        """
        cache_key = f"site:{site_id}"
        try:
            await self.redis.delete(cache_key)
            logger.info(f"Cache DELETE: {cache_key}")
        except Exception as e:
            logger.error(f"Redis delete error for {cache_key}: {e}")

    # ========== 组合缓存 (应用+授权) ==========

    async def get_app_and_auth(
        self, operator_id: UUID, app_code: str
    ) -> Optional[tuple[dict, dict]]:
        """批量获取应用和授权信息 (优化: 减少Redis往返次数)

        Args:
            operator_id: 运营商ID
            app_code: 应用代码

        Returns:
            Optional[tuple[dict, dict]]: (应用信息, 授权信息),如果任一不存在则返回None
        """
        try:
            # 使用pipeline批量获取,减少网络往返
            app_key = f"app:{app_code}"
            auth_key = f"auth:{operator_id}:{app_code}"

            # 这里简化处理,实际应该使用pipeline
            app_data = await self.get_application_by_code(app_code)
            auth_data = await self.get_authorization(operator_id, app_code)

            if app_data and auth_data:
                logger.debug(f"Batch cache HIT: {app_key} + {auth_key}")
                return (app_data, auth_data)

            logger.debug(f"Batch cache MISS: {app_key} or {auth_key}")
            return None
        except Exception as e:
            logger.error(f"Batch cache get error: {e}")
            return None

    async def set_app_and_auth(
        self,
        operator_id: UUID,
        app_code: str,
        app_data: dict,
        auth_data: dict,
        app_ttl: int = 1800,
        auth_ttl: int = 600,
    ) -> None:
        """批量缓存应用和授权信息

        Args:
            operator_id: 运营商ID
            app_code: 应用代码
            app_data: 应用数据字典
            auth_data: 授权数据字典
            app_ttl: 应用缓存过期时间(秒), 默认30分钟
            auth_ttl: 授权缓存过期时间(秒), 默认10分钟
        """
        await self.set_application(app_code, app_data, ttl=app_ttl)
        await self.set_authorization(operator_id, app_code, auth_data, ttl=auth_ttl)

    # ========== 缓存失效方法 (管理员操作时调用) ==========

    async def invalidate_application_cache(self, app_code: str) -> None:
        """使应用缓存失效 (管理员修改应用时调用)

        Args:
            app_code: 应用代码
        """
        await self.delete_application(app_code)
        logger.info(f"Invalidated application cache: {app_code}")

    async def invalidate_authorization_cache(self, operator_id: UUID, app_code: str) -> None:
        """使授权关系缓存失效 (管理员修改授权时调用)

        Args:
            operator_id: 运营商ID
            app_code: 应用代码
        """
        await self.delete_authorization(operator_id, app_code)
        logger.info(f"Invalidated authorization cache: operator={operator_id}, app={app_code}")

    async def invalidate_all_authorizations_for_app(self, app_code: str) -> None:
        """使某应用的所有授权缓存失效 (管理员修改应用时调用)

        当修改应用信息时，需要清除所有运营商对该应用的授权缓存。
        使用Redis SCAN命令查找所有匹配的key。

        Args:
            app_code: 应用代码
        """
        try:
            pattern = f"auth:*:{app_code}"
            deleted_count = await self.redis.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} authorization caches for app: {app_code}")
        except Exception as e:
            logger.error(f"Failed to invalidate authorizations for app {app_code}: {e}")

    async def invalidate_all_authorizations_for_operator(self, operator_id: UUID) -> None:
        """使某运营商的所有授权缓存失效 (管理员修改运营商时调用)

        Args:
            operator_id: 运营商ID
        """
        try:
            pattern = f"auth:{operator_id}:*"
            deleted_count = await self.redis.delete_pattern(pattern)
            logger.info(f"Invalidated {deleted_count} authorization caches for operator: {operator_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate authorizations for operator {operator_id}: {e}")

    async def invalidate_site_cache(self, site_id: UUID) -> None:
        """使运营点缓存失效 (运营商/管理员修改运营点时调用)

        Args:
            site_id: 运营点ID
        """
        await self.delete_site(site_id)
        logger.info(f"Invalidated site cache: {site_id}")
