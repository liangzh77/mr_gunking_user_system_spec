"""
API优化模块

提供API响应优化、请求批处理、智能缓存等功能
"""
import asyncio
import time
import json
import structlog
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, deque

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..cache.enhanced_cache import get_multi_cache, smart_cache
from ..metrics.enhanced_metrics import record_api_operation

logger = structlog.get_logger(__name__)


@dataclass
class ApiEndpointStats:
    """API端点统计"""
    endpoint: str
    method: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    max_duration: float = 0.0
    min_duration: float = float('inf')
    cache_hits: int = 0
    cache_misses: int = 0
    last_request: Optional[datetime] = None
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


@dataclass
class BatchRequest:
    """批处理请求"""
    request_id: str
    requests: List[Dict[str, Any]]
    timeout: int = 30
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ApiOptimizationConfig:
    """API优化配置"""
    enable_response_compression: bool = True
    enable_smart_caching: bool = True
    enable_request_batching: bool = True
    enable_rate_limiting: bool = True
    enable_deduplication: bool = True
    max_concurrent_requests: int = 100
    default_cache_ttl: int = 300
    slow_request_threshold: float = 1.0
    max_batch_size: int = 50
    batch_timeout: int = 5


class ApiOptimizer:
    """API优化器"""

    def __init__(self, config: ApiOptimizationConfig = None):
        self.config = config or ApiOptimizationConfig()
        self.cache = get_multi_cache()
        self._endpoint_stats: Dict[str, ApiEndpointStats] = {}
        self._rate_limiters: Dict[str, deque] = defaultdict(deque)
        self._pending_batches: Dict[str, BatchRequest] = {}
        self._deduplication_cache: Dict[str, asyncio.Future] = {}
        self._compression_enabled = {}
        self._max_stats_entries = 10000

    def track_api_request(self, endpoint: str, method: str,
                         duration: float, status_code: int,
                         cache_hit: bool = False):
        """跟踪API请求统计"""
        key = f"{method}:{endpoint}"

        if key not in self._endpoint_stats:
            self._endpoint_stats[key] = ApiEndpointStats(
                endpoint=endpoint,
                method=method
            )

        stats = self._endpoint_stats[key]
        stats.total_requests += 1
        stats.total_duration += duration
        stats.avg_duration = stats.total_duration / stats.total_requests
        stats.max_duration = max(stats.max_duration, duration)
        stats.min_duration = min(stats.min_duration, duration)
        stats.last_request = datetime.now()

        if status_code < 400:
            stats.successful_requests += 1
        else:
            stats.failed_requests += 1

        if cache_hit:
            stats.cache_hits += 1
        else:
            stats.cache_misses += 1

        # 更新比率
        stats.error_rate = stats.failed_requests / stats.total_requests
        stats.cache_hit_rate = stats.cache_hits / stats.total_requests

        # 记录慢请求
        if duration > self.config.slow_request_threshold:
            logger.warning("slow_api_request",
                         endpoint=endpoint,
                         method=method,
                         duration=duration,
                         status_code=status_code)

        # 清理旧统计
        self._cleanup_old_stats()

    def _cleanup_old_stats(self):
        """清理旧的统计数据"""
        if len(self._endpoint_stats) > self._max_stats_entries:
            # 按最后请求时间排序，删除最旧的
            sorted_stats = sorted(
                self._endpoint_stats.items(),
                key=lambda x: x[1].last_request or datetime.min
            )

            # 保留最近的一半
            keep_count = self._max_stats_entries // 2
            self._endpoint_stats = dict(sorted_stats[-keep_count:])

    async def get_endpoint_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取端点统计信息"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        active_stats = {
            key: stats for key, stats in self._endpoint_stats.items()
            if stats.last_request and stats.last_request >= cutoff_time
        }

        if not active_stats:
            return {
                "period_hours": hours,
                "total_endpoints": 0,
                "message": "No requests in the specified period"
            }

        # 汇总统计
        total_requests = sum(stats.total_requests for stats in active_stats.values())
        total_successful = sum(stats.successful_requests for stats in active_stats.values())
        total_failed = total_requests - total_successful
        avg_response_time = sum(stats.avg_duration for stats in active_stats.values()) / len(active_stats)

        # 按性能排序
        slowest_endpoints = sorted(
            active_stats.items(),
            key=lambda x: x[1].avg_duration,
            reverse=True
        )[:10]

        # 按请求量排序
        busiest_endpoints = sorted(
            active_stats.items(),
            key=lambda x: x[1].total_requests,
            reverse=True
        )[:10]

        # 错误率最高的端点
        highest_error_endpoints = sorted(
            active_stats.items(),
            key=lambda x: x[1].error_rate,
            reverse=True
        )[:5]

        return {
            "period_hours": hours,
            "summary": {
                "total_endpoints": len(active_stats),
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "success_rate": total_successful / total_requests if total_requests > 0 else 0,
                "avg_response_time": avg_response_time
            },
            "slowest_endpoints": [
                {
                    "endpoint": stats.endpoint,
                    "method": stats.method,
                    "avg_duration": stats.avg_duration,
                    "max_duration": stats.max_duration,
                    "total_requests": stats.total_requests
                }
                for _, stats in slowest_endpoints
            ],
            "busiest_endpoints": [
                {
                    "endpoint": stats.endpoint,
                    "method": stats.method,
                    "total_requests": stats.total_requests,
                    "avg_duration": stats.avg_duration,
                    "error_rate": stats.error_rate
                }
                for _, stats in busiest_endpoints
            ],
            "highest_error_endpoints": [
                {
                    "endpoint": stats.endpoint,
                    "method": stats.method,
                    "error_rate": stats.error_rate,
                    "failed_requests": stats.failed_requests,
                    "total_requests": stats.total_requests
                }
                for _, stats in highest_error_endpoints if stats.error_rate > 0
            ],
            "detailed_stats": {
                key: {
                    "total_requests": stats.total_requests,
                    "avg_duration": stats.avg_duration,
                    "error_rate": stats.error_rate,
                    "cache_hit_rate": stats.cache_hit_rate
                }
                for key, stats in active_stats.items()
            }
        }

    def smart_cache_key(self, request: Request, endpoint_config: Dict = None) -> Optional[str]:
        """智能缓存键生成"""
        if not self.config.enable_smart_caching:
            return None

        # 检查端点是否支持缓存
        if endpoint_config and not endpoint_config.get('cacheable', False):
            return None

        # 只缓存GET请求
        if request.method != 'GET':
            return None

        # 基础缓存键
        key_parts = [
            "api_cache",
            request.url.path
        ]

        # 添加查询参数（排序后）
        if request.query_params:
            sorted_params = sorted(request.query_params.items())
            query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(query_string)

        # 添加用户信息（如果需要用户隔离）
        user_id = getattr(request.state, 'user_id', None)
        if user_id and endpoint_config and endpoint_config.get('user_specific', False):
            key_parts.append(f"user:{user_id}")

        # 添加角色信息（如果需要角色隔离）
        user_role = getattr(request.state, 'user_role', None)
        if user_role and endpoint_config and endpoint_config.get('role_specific', False):
            key_parts.append(f"role:{user_role}")

        return ":".join(key_parts)

    async def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的响应"""
        if not cache_key:
            return None

        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                logger.debug("api_cache_hit", cache_key=cache_key)
                return cached_data

            logger.debug("api_cache_miss", cache_key=cache_key)
            return None

        except Exception as e:
            logger.error("api_cache_get_error", cache_key=cache_key, error=str(e))
            return None

    async def cache_response(self, cache_key: str, response: Response,
                           ttl: int = None) -> bool:
        """缓存响应"""
        if not cache_key:
            return False

        try:
            cache_ttl = ttl or self.config.default_cache_ttl

            # 序列化响应数据
            cache_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": getattr(response, "body", None),
                "media_type": getattr(response, "media_type", None)
            }

            await self.cache.set(cache_key, cache_data, ttl=cache_ttl)
            logger.debug("api_cache_set", cache_key=cache_key, ttl=cache_ttl)
            return True

        except Exception as e:
            logger.error("api_cache_set_error", cache_key=cache_key, error=str(e))
            return False

    def should_compress_response(self, request: Request, response: Response) -> bool:
        """判断是否应该压缩响应"""
        if not self.config.enable_response_compression:
            return False

        # 检查客户端是否支持压缩
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return False

        # 检查内容类型
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript"
        ]

        if not any(ct in content_type for ct in compressible_types):
            return False

        # 检查响应大小
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < 1024:  # 小于1KB不压缩
            return False

        # 检查是否已经压缩
        if response.headers.get("content-encoding"):
            return False

        return True

    async def check_rate_limit(self, request: Request, limit: int = 100,
                             window: int = 60) -> bool:
        """检查API限流"""
        if not self.config.enable_rate_limiting:
            return True

        # 获取客户端标识
        client_ip = request.client.host
        user_id = getattr(request.state, 'user_id', None)
        identifier = user_id or client_ip

        # 生成限流键
        rate_limit_key = f"rate_limit:{identifier}:{request.url.path}"

        # 清理过期记录
        now = time.time()
        cutoff_time = now - window
        requests_queue = self._rate_limiters[rate_limit_key]

        while requests_queue and requests_queue[0] < cutoff_time:
            requests_queue.popleft()

        # 检查是否超过限制
        if len(requests_queue) >= limit:
            logger.warning("rate_limit_exceeded",
                         identifier=identifier,
                         endpoint=request.url.path,
                         current_count=len(requests_queue),
                         limit=limit)
            return False

        # 记录当前请求
        requests_queue.append(now)

        # 设置过期清理
        if len(requests_queue) == 1:  # 第一个请求
            asyncio.create_task(self._cleanup_rate_limit(rate_limit_key, window))

        return True

    async def _cleanup_rate_limit(self, key: str, window: int):
        """清理过期的限流记录"""
        await asyncio.sleep(window)
        self._rate_limiters.pop(key, None)

    async def deduplicate_request(self, request: Request) -> Optional[asyncio.Future]:
        """请求去重"""
        if not self.config.enable_deduplication:
            return None

        # 只对写操作进行去重
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return None

        # 生成去重键
        dedup_key = self._generate_dedup_key(request)

        # 检查是否有相同的请求正在处理
        if dedup_key in self._deduplication_cache:
            future = self._deduplication_cache[dedup_key]
            if not future.done():
                logger.debug("request_deduplicated",
                           method=request.method,
                           path=request.url.path,
                           dedup_key=dedup_key)
                return future

        # 创建新的Future
        future = asyncio.Future()
        self._deduplication_cache[dedup_key] = future

        # 设置清理任务
        asyncio.create_task(self._cleanup_deduplication(dedup_key))

        return None

    def _generate_dedup_key(self, request: Request) -> str:
        """生成去重键"""
        key_parts = [
            "dedup",
            request.method.lower(),
            request.url.path
        ]

        # 添加请求体哈希（对于写操作）
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = getattr(request, '_body', b'')
                import hashlib
                body_hash = hashlib.md5(body).hexdigest()
                key_parts.append(body_hash)
            except Exception:
                pass

        # 添加用户标识
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            key_parts.append(f"user:{user_id}")

        return ":".join(key_parts)

    async def _cleanup_deduplication(self, dedup_key: str):
        """清理去重缓存"""
        await asyncio.sleep(30)  # 30秒后清理
        self._deduplication_cache.pop(dedup_key, None)

    async def optimize_batch_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化批处理请求"""
        if not self.config.enable_request_batching or not requests:
            return requests

        # 按端点分组
        endpoint_groups = defaultdict(list)
        for i, req in enumerate(requests):
            endpoint = f"{req.get('method', 'GET')}:{req.get('path', '/')}"
            endpoint_groups[endpoint].append((i, req))

        # 并发执行不同端点的请求
        results = [None] * len(requests)
        tasks = []

        for endpoint, grouped_requests in endpoint_groups.items():
            task = self._execute_endpoint_batch(grouped_requests, results)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    async def _execute_endpoint_batch(self, grouped_requests: List[Tuple[int, Dict]],
                                    results: List):
        """执行单个端点的批处理请求"""
        method, path = grouped_requests[0][1].get('method', 'GET'), grouped_requests[0][1].get('path', '/')

        try:
            # 这里应该调用实际的API处理逻辑
            # 简化实现，实际需要与路由系统集成
            for index, request in grouped_requests:
                # 模拟API响应
                results[index] = {
                    "status": "success",
                    "data": f"Response for {method} {path}",
                    "index": index
                }

        except Exception as e:
            # 所有请求都失败
            for index, _ in grouped_requests:
                results[index] = {
                    "status": "error",
                    "error": str(e),
                    "index": index
                }

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """获取优化建议"""
        recommendations = []

        # 分析慢端点
        slow_endpoints = [
            (key, stats) for key, stats in self._endpoint_stats.items()
            if stats.avg_duration > self.config.slow_request_threshold
        ]

        if slow_endpoints:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "title": "发现慢API端点",
                "description": f"有{len(slow_endpoints)}个端点平均响应时间超过{self.config.slow_request_threshold}秒",
                "details": [
                    f"{stats.method} {stats.endpoint}: {stats.avg_duration:.3f}s"
                    for _, stats in slow_endpoints[:5]
                ],
                "actions": [
                    "检查数据库查询性能",
                    "添加适当的索引",
                    "实施缓存策略",
                    "考虑异步处理"
                ]
            })

        # 分析高错误率端点
        high_error_endpoints = [
            (key, stats) for key, stats in self._endpoint_stats.items()
            if stats.error_rate > 0.1 and stats.total_requests > 10
        ]

        if high_error_endpoints:
            recommendations.append({
                "type": "reliability",
                "priority": "high",
                "title": "发现高错误率端点",
                "description": f"有{len(high_error_endpoints)}个端点错误率超过10%",
                "details": [
                    f"{stats.method} {stats.endpoint}: {stats.error_rate:.1%}"
                    for _, stats in high_error_endpoints[:5]
                ],
                "actions": [
                    "检查错误日志",
                    "加强输入验证",
                    "改进错误处理",
                    "添加重试机制"
                ]
            })

        # 分析缓存命中率
        low_cache_hit_endpoints = [
            (key, stats) for key, stats in self._endpoint_stats.items()
            if stats.cache_hit_rate < 0.3 and stats.total_requests > 50
        ]

        if low_cache_hit_endpoints:
            recommendations.append({
                "type": "caching",
                "priority": "medium",
                "title": "缓存命中率较低",
                "description": f"有{len(low_cache_hit_endpoints)}个端点缓存命中率低于30%",
                "details": [
                    f"{stats.method} {stats.endpoint}: {stats.cache_hit_rate:.1%}"
                    for _, stats in low_cache_hit_endpoints[:5]
                ],
                "actions": [
                    "调整缓存策略",
                    "增加缓存时间",
                    "优化缓存键设计",
                    "考虑多级缓存"
                ]
            })

        # 分析热点端点
        busy_endpoints = [
            (key, stats) for key, stats in self._endpoint_stats.items()
            if stats.total_requests > 1000
        ]

        if busy_endpoints:
            recommendations.append({
                "type": "scaling",
                "priority": "medium",
                "title": "发现热点端点",
                "description": f"有{len(busy_endpoints)}个端点请求量较大，可能需要扩容",
                "details": [
                    f"{stats.method} {stats.endpoint}: {stats.total_requests} requests"
                    for _, stats in busy_endpoints[:5]
                ],
                "actions": [
                    "实施负载均衡",
                    "增加缓存策略",
                    "考虑读写分离",
                    "优化数据库连接"
                ]
            })

        return recommendations

    async def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        try:
            # 获取统计数据
            endpoint_stats = await self.get_endpoint_statistics(hours=24)
            recommendations = self.get_optimization_recommendations()

            # 计算性能评分
            performance_score = self._calculate_performance_score()

            # 获取缓存统计
            cache_stats = self.cache.get_stats()

            report = {
                "performance_score": performance_score,
                "summary": {
                    "total_endpoints": len(self._endpoint_stats),
                    "avg_response_time": endpoint_stats.get("summary", {}).get("avg_response_time", 0),
                    "success_rate": endpoint_stats.get("summary", {}).get("success_rate", 0),
                    "cache_hit_rate": cache_stats.get("global", {}).get("hit_rate", 0)
                },
                "endpoint_statistics": endpoint_stats,
                "cache_statistics": cache_stats,
                "optimization_recommendations": recommendations,
                "configuration": {
                    "response_compression": self.config.enable_response_compression,
                    "smart_caching": self.config.enable_smart_caching,
                    "request_batching": self.config.enable_request_batching,
                    "rate_limiting": self.config.enable_rate_limiting,
                    "deduplication": self.config.enable_deduplication
                },
                "timestamp": datetime.now().isoformat()
            }

            # 缓存报告
            await self.cache.set("api_performance_report", report, ttl=300)

            logger.info("api_performance_report_generated",
                        performance_score=performance_score,
                        recommendations_count=len(recommendations))

            return report

        except Exception as e:
            logger.error("api_performance_report_failed", error=str(e))
            return {"error": str(e)}

    def _calculate_performance_score(self) -> float:
        """计算API性能评分"""
        if not self._endpoint_stats:
            return 100.0

        score = 100.0

        # 基于平均响应时间评分
        avg_duration = sum(stats.avg_duration for stats in self._endpoint_stats.values()) / len(self._endpoint_stats)
        if avg_duration > 2.0:
            score -= 30
        elif avg_duration > 1.0:
            score -= 15
        elif avg_duration > 0.5:
            score -= 5

        # 基于错误率评分
        avg_error_rate = sum(stats.error_rate for stats in self._endpoint_stats.values()) / len(self._endpoint_stats)
        if avg_error_rate > 0.1:
            score -= 40
        elif avg_error_rate > 0.05:
            score -= 20
        elif avg_error_rate > 0.01:
            score -= 10

        # 基于缓存命中率评分
        cache_hit_rates = [stats.cache_hit_rate for stats in self._endpoint_stats.values() if stats.total_requests > 10]
        if cache_hit_rates:
            avg_cache_hit_rate = sum(cache_hit_rates) / len(cache_hit_rates)
            if avg_cache_hit_rate < 0.3:
                score -= 20
            elif avg_cache_hit_rate < 0.5:
                score -= 10
            elif avg_cache_hit_rate > 0.8:
                score += 10  # 奖励高缓存命中率

        return max(score, 0)


def api_cache(ttl: int = 300, key_builder: Optional[Callable] = None):
    """API缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_multi_cache()

            # 生成缓存键
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"api_cache:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug("api_decorator_cache_hit", function=func.__name__)
                return cached_result

            # 执行函数
            logger.debug("api_decorator_cache_miss", function=func.__name__)
            result = await func(*args, **kwargs)

            # 存储到缓存
            await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator


def rate_limit_decorator(max_requests: int, window_seconds: int = 60):
    """API限流装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 这里应该实现具体的限流逻辑
            # 简化实现，实际应该与请求上下文集成
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def init_api_optimization(app, config: dict) -> ApiOptimizer:
    """初始化API优化系统"""
    try:
        # 创建配置
        api_config = ApiOptimizationConfig(
            enable_response_compression=config.get('enable_response_compression', True),
            enable_smart_caching=config.get('enable_smart_caching', True),
            enable_request_batching=config.get('enable_request_batching', True),
            enable_rate_limiting=config.get('enable_rate_limiting', True),
            enable_deduplication=config.get('enable_deduplication', True),
            max_concurrent_requests=config.get('max_concurrent_requests', 100),
            default_cache_ttl=config.get('default_cache_ttl', 300),
            slow_request_threshold=config.get('slow_request_threshold', 1.0),
            max_batch_size=config.get('max_batch_size', 50),
            batch_timeout=config.get('batch_timeout', 5)
        )

        optimizer = ApiOptimizer(api_config)

        # 添加中间件（如果需要）
        if config.get('add_middleware', True):
            from ..middleware.performance import (
                CompressionMiddleware,
                CacheMiddleware,
                RequestDeduplicationMiddleware,
                PerformanceMonitoringMiddleware
            )

            app.add_middleware(PerformanceMonitoringMiddleware)

            if api_config.enable_response_compression:
                app.add_middleware(CompressionMiddleware)

            if api_config.enable_smart_caching:
                app.add_middleware(CacheMiddleware,
                                 cache_ttl=api_config.default_cache_ttl)

            if api_config.enable_deduplication:
                app.add_middleware(RequestDeduplicationMiddleware)

        logger.info("api_optimization_initialized",
                   compression=api_config.enable_response_compression,
                   caching=api_config.enable_smart_caching,
                   rate_limiting=api_config.enable_rate_limiting)

        return optimizer

    except Exception as e:
        logger.error("api_optimization_init_error", error=str(e))
        raise