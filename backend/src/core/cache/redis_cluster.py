"""
Redis集群配置和连接管理
支持主从复制和Sentinel高可用
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

import redis
from redis.asyncio import Redis as AsyncRedis, ConnectionPool as AsyncConnectionPool
from redis.sentinel import Sentinel as RedisSentinel
from redis.exceptions import (
    ConnectionError,
    RedisError,
    AuthenticationError,
    TimeoutError,
    MasterNotFoundError
)

logger = logging.getLogger(__name__)

@dataclass
class RedisConfig:
    """Redis配置类"""
    # 基本连接配置
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0

    # Sentinel配置
    sentinel_enabled: bool = False
    sentinel_hosts: List[tuple] = None
    sentinel_service_name: str = "mymaster"
    sentinel_timeout: int = 10

    # 连接池配置
    max_connections: int = 20
    max_idle_time: int = 300
    idle_check_interval: int = 30

    # 超时配置
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    command_timeout: int = 5

    # 重试配置
    retry_on_timeout: bool = True
    retry_on_error: List[str] = None

    # 其他配置
    decode_responses: bool = True
    health_check_interval: int = 30
    ssl: bool = False
    ssl_cert_reqs: str = "required"

    def __post_init__(self):
        if self.sentinel_hosts is None:
            self.sentinel_hosts = [("localhost", 26379), ("localhost", 26380), ("localhost", 26381)]
        if self.retry_on_error is None:
            self.retry_on_error = ["ConnectionError", "TimeoutError"]

    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """从环境变量创建配置"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            database=int(os.getenv("REDIS_DATABASE", "0")),

            sentinel_enabled=os.getenv("REDIS_SENTINEL_ENABLED", "false").lower() == "true",
            sentinel_hosts=json.loads(os.getenv("REDIS_SENTINEL_HOSTS", '[]')) or [
                ("localhost", 26379), ("localhost", 26380), ("localhost", 26381)
            ],
            sentinel_service_name=os.getenv("REDIS_SENTINEL_SERVICE_NAME", "mymaster"),
            sentinel_timeout=int(os.getenv("REDIS_SENTINEL_TIMEOUT", "10")),

            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
            max_idle_time=int(os.getenv("REDIS_MAX_IDLE_TIME", "300")),
            idle_check_interval=int(os.getenv("REDIS_IDLE_CHECK_INTERVAL", "30")),

            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
            command_timeout=int(os.getenv("REDIS_COMMAND_TIMEOUT", "5")),

            retry_on_timeout=os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true",
            retry_on_error=json.loads(os.getenv("REDIS_RETRY_ON_ERROR", '["ConnectionError", "TimeoutError"]')),

            decode_responses=os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true",
            health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
        )

class RedisClusterManager:
    """Redis集群管理器"""

    def __init__(self, config: RedisConfig):
        self.config = config
        self._master_client: Optional[redis.Redis] = None
        self._slave_clients: List[redis.Redis] = []
        self._sentinel: Optional[RedisSentinel] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional[AsyncConnectionPool] = None
        self._async_client: Optional[AsyncRedis] = None
        self._last_health_check: Optional[datetime] = None
        self._connection_stats = {
            "connections_created": 0,
            "connections_failed": 0,
            "reconnections": 0,
            "last_error": None
        }

    async def initialize(self) -> bool:
        """初始化Redis连接"""
        try:
            if self.config.sentinel_enabled:
                success = await self._initialize_sentinel()
            else:
                success = await self._initialize_direct()

            if success:
                await self._initialize_async_client()
                await self._health_check()
                logger.info("Redis集群初始化成功")
                return True
            else:
                logger.error("Redis集群初始化失败")
                return False

        except Exception as e:
            logger.error(f"Redis集群初始化异常: {e}")
            self._connection_stats["last_error"] = str(e)
            return False

    async def _initialize_direct(self) -> bool:
        """初始化直接连接"""
        try:
            # 创建连接池
            self._connection_pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.database,
                max_connections=self.config.max_connections,
                max_idle_time=self.config.max_idle_time,
                idle_check_interval=self.config.idle_check_interval,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=self.config.decode_responses,
                health_check_interval=self.config.health_check_interval,
                ssl=self.config.ssl,
                ssl_cert_reqs=self.config.ssl_cert_reqs
            )

            # 创建主客户端
            self._master_client = redis.Redis(connection_pool=self._connection_pool)

            # 测试连接
            self._master_client.ping()
            self._connection_stats["connections_created"] += 1

            logger.info(f"Redis直接连接成功: {self.config.host}:{self.config.port}")
            return True

        except Exception as e:
            logger.error(f"Redis直接连接失败: {e}")
            self._connection_stats["connections_failed"] += 1
            self._connection_stats["last_error"] = str(e)
            return False

    async def _initialize_sentinel(self) -> bool:
        """初始化Sentinel连接"""
        try:
            # 创建Sentinel客户端
            self._sentinel = RedisSentinel(
                sentinels=self.config.sentinel_hosts,
                socket_timeout=self.config.sentinel_timeout,
                password=self.config.password,
                decode_responses=self.config.decode_responses
            )

            # 获取主节点
            master = self._sentinel.master_for(
                self.config.sentinel_service_name,
                socket_timeout=self.config.socket_timeout,
                password=self.config.password,
                decode_responses=self.config.decode_responses
            )

            # 测试主节点连接
            master.ping()
            self._master_client = master
            self._connection_stats["connections_created"] += 1

            # 获取从节点用于读操作
            try:
                slave = self._sentinel.slave_for(
                    self.config.sentinel_service_name,
                    socket_timeout=self.config.socket_timeout,
                    password=self.config.password,
                    decode_responses=self.config.decode_responses
                )
                slave.ping()
                self._slave_clients.append(slave)
                logger.info("Redis Sentinel从节点连接成功")
            except Exception as e:
                logger.warning(f"Redis Sentinel从节点连接失败: {e}")

            logger.info(f"Redis Sentinel连接成功: {self.config.sentinel_service_name}")
            return True

        except Exception as e:
            logger.error(f"Redis Sentinel连接失败: {e}")
            self._connection_stats["connections_failed"] += 1
            self._connection_stats["last_error"] = str(e)
            return False

    async def _initialize_async_client(self) -> bool:
        """初始化异步客户端"""
        try:
            if self.config.sentinel_enabled and self._sentinel:
                # Sentinel模式下的异步客户端
                self._async_client = AsyncRedis(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.database,
                    decode_responses=self.config.decode_responses,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout
                )
            else:
                # 直接连接模式下的异步客户端
                self._async_pool = AsyncConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.database,
                    max_connections=self.config.max_connections,
                    decode_responses=self.config.decode_responses,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout
                )
                self._async_client = AsyncRedis(connection_pool=self._async_pool)

            # 测试异步连接
            await self._async_client.ping()
            logger.info("Redis异步客户端初始化成功")
            return True

        except Exception as e:
            logger.error(f"Redis异步客户端初始化失败: {e}")
            return False

    async def _health_check(self) -> bool:
        """健康检查"""
        try:
            if self._master_client:
                self._master_client.ping()

            # 检查从节点
            for slave in self._slave_clients:
                slave.ping()

            self._last_health_check = datetime.now()
            return True

        except Exception as e:
            logger.error(f"Redis健康检查失败: {e}")
            return False

    async def get_master_client(self) -> redis.Redis:
        """获取主节点客户端（用于写操作）"""
        if not self._master_client:
            await self.initialize()
        return self._master_client

    async def get_read_client(self) -> redis.Redis:
        """获取读节点客户端（用于读操作）"""
        # 优先使用从节点
        if self._slave_clients:
            try:
                # 简单的负载均衡：轮流使用从节点
                import time
                index = int(time.time()) % len(self._slave_clients)
                slave = self._slave_clients[index]
                slave.ping()  # 测试连接
                return slave
            except:
                # 从节点不可用时使用主节点
                pass

        # 使用主节点
        return await self.get_master_client()

    async def get_async_client(self) -> AsyncRedis:
        """获取异步客户端"""
        if not self._async_client:
            await self.initialize()
        return self._async_client

    async def execute_command(self, command: str, *args, **kwargs) -> Any:
        """执行Redis命令"""
        try:
            client = await self.get_master_client()
            return client.execute_command(command, *args, **kwargs)
        except Exception as e:
            logger.error(f"Redis命令执行失败: {command}, 错误: {e}")
            raise

    async def execute_read_command(self, command: str, *args, **kwargs) -> Any:
        """执行读命令（优先使用从节点）"""
        try:
            client = await self.get_read_client()
            return client.execute_command(command, *args, **kwargs)
        except Exception as e:
            logger.error(f"Redis读命令执行失败: {command}, 错误: {e}")
            raise

    async def close(self):
        """关闭连接"""
        try:
            if self._master_client:
                self._master_client.close()
            for slave in self._slave_clients:
                slave.close()
            if self._async_client:
                await self._async_client.close()
            if self._async_pool:
                await self._async_pool.disconnect()
            logger.info("Redis连接已关闭")
        except Exception as e:
            logger.error(f"关闭Redis连接失败: {e}")

    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        info = {
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "sentinel_enabled": self.config.sentinel_enabled,
                "max_connections": self.config.max_connections
            },
            "stats": self._connection_stats.copy(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "master_connected": self._master_client is not None,
            "slave_clients_count": len(self._slave_clients),
            "async_client_connected": self._async_client is not None
        }

        # 获取Redis服务器信息
        try:
            if self._master_client:
                server_info = self._master_client.info()
                info["server"] = {
                    "redis_version": server_info.get("redis_version"),
                    "used_memory_human": server_info.get("used_memory_human"),
                    "connected_clients": server_info.get("connected_clients"),
                    "total_commands_processed": server_info.get("total_commands_processed")
                }
        except:
            pass

        return info

    async def failover_test(self) -> Dict[str, Any]:
        """故障转移测试（仅在Sentinel模式下）"""
        if not self.config.sentinel_enabled or not self._sentinel:
            return {"error": "Sentinel模式未启用"}

        try:
            # 触发故障转移
            result = self._sentinel.failover(self.config.sentinel_service_name)

            # 等待故障转移完成
            await asyncio.sleep(5)

            # 重新初始化连接
            await self.initialize()

            return {
                "success": True,
                "message": "故障转移测试完成",
                "new_master_info": await self.get_connection_info()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class RedisService:
    """Redis服务类，提供高级操作接口"""

    def __init__(self, cluster_manager: RedisClusterManager):
        self.cluster = cluster_manager

    async def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            client = await self.cluster.get_master_client()
            if ttl:
                return client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            else:
                return client.set(key, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")
            return False

    async def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            client = await self.cluster.get_read_client()
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e}")
            return None

    async def delete_cache(self, *keys: str) -> int:
        """删除缓存"""
        try:
            client = await self.cluster.get_master_client()
            return client.delete(*keys)
        except Exception as e:
            logger.error(f"删除缓存失败: {keys}, 错误: {e}")
            return 0

    async def cache_exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            client = await self.cluster.get_read_client()
            return client.exists(key) > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {key}, 错误: {e}")
            return False

    async def increment_cache(self, key: str, amount: int = 1) -> Optional[int]:
        """递增缓存值"""
        try:
            client = await self.cluster.get_master_client()
            return client.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增缓存失败: {key}, 错误: {e}")
            return None

    async def get_cache_ttl(self, key: str) -> int:
        """获取缓存剩余时间"""
        try:
            client = await self.cluster.get_read_client()
            return client.ttl(key)
        except Exception as e:
            logger.error(f"获取缓存TTL失败: {key}, 错误: {e}")
            return -1

    async def set_cache_with_pipeline(self, operations: List[Dict]) -> bool:
        """使用管道批量操作"""
        try:
            client = await self.cluster.get_master_client()
            pipe = client.pipeline()

            for op in operations:
                method = op.get("method")
                args = op.get("args", [])
                kwargs = op.get("kwargs", {})

                if method == "set":
                    pipe.set(*args, **kwargs)
                elif method == "setex":
                    pipe.setex(*args, **kwargs)
                elif method == "delete":
                    pipe.delete(*args)
                elif method == "incrby":
                    pipe.incrby(*args, **kwargs)

            pipe.execute()
            return True

        except Exception as e:
            logger.error(f"管道操作失败: {e}")
            return False

# 全局Redis集群管理器实例
redis_cluster_manager: Optional[RedisClusterManager] = None
redis_service: Optional[RedisService] = None

async def init_redis_cluster(config: Optional[RedisConfig] = None) -> bool:
    """初始化Redis集群"""
    global redis_cluster_manager, redis_service

    if config is None:
        config = RedisConfig.from_env()

    redis_cluster_manager = RedisClusterManager(config)
    success = await redis_cluster_manager.initialize()

    if success:
        redis_service = RedisService(redis_cluster_manager)

    return success

async def get_redis_service() -> RedisService:
    """获取Redis服务实例"""
    if redis_service is None:
        await init_redis_cluster()
    return redis_service

async def get_redis_cluster_manager() -> RedisClusterManager:
    """获取Redis集群管理器实例"""
    if redis_cluster_manager is None:
        await init_redis_cluster()
    return redis_cluster_manager

async def close_redis_cluster():
    """关闭Redis集群连接"""
    global redis_cluster_manager, redis_service

    if redis_cluster_manager:
        await redis_cluster_manager.close()

    redis_cluster_manager = None
    redis_service = None