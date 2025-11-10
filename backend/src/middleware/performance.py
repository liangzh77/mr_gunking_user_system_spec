"""
性能优化中间件

提供API响应时间优化、请求去重、压缩等功能
"""
import time
import gzip
import json
import structlog
import hashlib
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from dataclasses import dataclass

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

# 注释掉不存在的依赖
# from ..core.cache.enhanced_cache import get_multi_cache, smart_cache
# from ..core.metrics.enhanced_metrics import record_api_operation

logger = structlog.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    request_id: str
    method: str
    path: str
    start_time: float
    end_time: float
    duration_ms: float
    status_code: int
    response_size: int
    cache_hit: bool = False
    compressed: bool = False


class CompressionMiddleware(BaseHTTPMiddleware):
    """响应压缩中间件"""

    def __init__(self,
                 app,
                 min_size: int = 1024,
                 compressible_types: List[str] = None,
                 excluded_paths: List[str] = None):
        super().__init__(app)
        self.min_size = min_size
        self.compressible_types = compressible_types or [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/xml",
            "text/xml"
        ]
        self.excluded_paths = excluded_paths or ["/metrics", "/health", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next):
        # 检查是否应该压缩
        if self._should_skip_compression(request):
            return await call_next(request)

        response = await call_next(request)

        # 检查响应是否应该被压缩
        if not self._should_compress_response(request, response):
            return response

        # 压缩响应
        return await self._compress_response(response)

    def _should_skip_compression(self, request: Request) -> bool:
        """检查是否应该跳过压缩"""
        path = request.url.path
        return any(path.startswith(excluded) for excluded in self.excluded_paths)

    def _should_compress_response(self, request: Request, response: Response) -> bool:
        """检查响应是否应该被压缩"""
        # 检查客户端是否支持压缩
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return False

        # 检查内容类型
        content_type = response.headers.get("content-type", "").split(";")[0]
        if content_type not in self.compressible_types:
            return False

        # 检查响应大小
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.min_size:
            return False

        # 检查是否已经压缩
        if response.headers.get("content-encoding"):
            return False

        return True

    async def _compress_response(self, response: Response) -> Response:
        """压缩响应"""
        try:
            # 获取响应内容
            if hasattr(response, "body"):
                body = response.body
            elif hasattr(response, "body_iterator"):
                # 流式响应暂不压缩
                return response
            else:
                return response

            # 检查是否为JSON响应
            if isinstance(response, JSONResponse):
                content = json.dumps(response.content).encode()
            else:
                content = body

            # 检查大小
            if len(content) < self.min_size:
                return response

            # 压缩内容
            compressed_body = gzip.compress(content)

            # 创建新的响应
            headers = dict(response.headers)
            headers["content-encoding"] = "gzip"
            headers["content-length"] = str(len(compressed_body))

            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )

        except Exception as e:
            logger.error("compression_error", error=str(e))
            return response


class CacheMiddleware(BaseHTTPMiddleware):
    """API响应缓存中间件"""

    def __init__(self,
                 app,
                 cache_ttl: int = 300,
                 cacheable_methods: List[str] = None,
                 cacheable_status_codes: List[int] = None,
                 cache_key_builder: Optional[Callable] = None):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_methods = cacheable_methods or ["GET"]
        self.cacheable_status_codes = cacheable_status_codes or [200, 301, 302]
        self.cache_key_builder = cache_key_builder
        # self.cache = get_multi_cache()  # 暂时禁用，依赖不存在

    async def dispatch(self, request: Request, call_next):
        # 只缓存GET请求
        if request.method not in self.cacheable_methods:
            return await call_next(request)

        # 生成缓存键
        cache_key = self._build_cache_key(request)

        # 尝试从缓存获取
        cached_response = await self.cache.get(cache_key)
        if cached_response:
            logger.debug("api_cache_hit", path=request.url.path, cache_key=cache_key)
            return self._create_response_from_cache(cached_response)

        # 执行请求
        response = await call_next(request)

        # 检查是否应该缓存
        if self._should_cache_response(response):
            cache_data = self._serialize_response(response)
            await self.cache.set(cache_key, cache_data, ttl=self.cache_ttl)
            logger.debug("api_cache_set", path=request.url.path, cache_key=cache_key)

        return response

    def _build_cache_key(self, request: Request) -> str:
        """构建缓存键"""
        if self.cache_key_builder:
            return self.cache_key_builder(request)

        # 默认缓存键构建
        key_parts = [
            "api_cache",
            request.method.lower(),
            request.url.path
        ]

        # 添加查询参数
        if request.query_params:
            sorted_params = sorted(request.query_params.items())
            query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(query_string)

        # 添加用户标识（如果有）
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            key_parts.append(f"user:{user_id}")

        return ":".join(key_parts)

    def _should_cache_response(self, response: Response) -> bool:
        """检查响应是否应该被缓存"""
        # 检查状态码
        if response.status_code not in self.cacheable_status_codes:
            return False

        # 检查是否有缓存控制头
        cache_control = response.headers.get("cache-control", "")
        if "no-cache" in cache_control or "no-store" in cache_control:
            return False

        # 检查内容类型
        content_type = response.headers.get("content-type", "")
        if not content_type or "application/json" not in content_type:
            return False

        return True

    def _serialize_response(self, response: Response) -> Dict[str, Any]:
        """序列化响应"""
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": getattr(response, "body", None),
            "media_type": getattr(response, "media_type", None)
        }

    def _create_response_from_cache(self, cached_data: Dict[str, Any]) -> Response:
        """从缓存数据创建响应"""
        return Response(
            content=cached_data["body"],
            status_code=cached_data["status_code"],
            headers=cached_data["headers"],
            media_type=cached_data["media_type"]
        )


class RequestDeduplicationMiddleware(BaseHTTPMiddleware):
    """请求去重中间件"""

    def __init__(self,
                 app,
                 dedup_window: int = 5,
                 dedup_methods: List[str] = None,
                 key_builder: Optional[Callable] = None):
        super().__init__(app)
        self.dedup_window = dedup_window
        self.dedup_methods = dedup_methods or ["POST", "PUT", "PATCH", "DELETE"]
        self.key_builder = key_builder
        self._pending_requests: Dict[str, Any] = {}

    async def dispatch(self, request: Request, call_next):
        # 只对指定方法进行去重
        if request.method not in self.dedup_methods:
            return await call_next(request)

        # 生成去重键
        dedup_key = self._build_dedup_key(request)

        # 检查是否有相同的请求正在处理
        if dedup_key in self._pending_requests:
            logger.debug("request_deduplication",
                        method=request.method,
                        path=request.url.path,
                        dedup_key=dedup_key)

            # 等待现有请求完成
            return await self._pending_requests[dedup_key]

        # 创建请求等待对象
        request_future = asyncio.Future()

        # 注册请求
        self._pending_requests[dedup_key] = request_future

        try:
            # 执行请求
            response = await call_next(request)

            # 设置结果并等待其他请求
            if not request_future.done():
                request_future.set_result(response)

            return response

        except Exception as e:
            # 设置异常并传播
            if not request_future.done():
                request_future.set_exception(e)
            raise

        finally:
            # 清理请求记录
            self._pending_requests.pop(dedup_key, None)

    def _build_dedup_key(self, request: Request) -> str:
        """构建去重键"""
        if self.key_builder:
            return self.key_builder(request)

        # 默认去重键构建
        key_parts = [
            "dedup",
            request.method.lower(),
            request.url.path
        ]

        # 添加请求体哈希（对POST/PUT/PATCH请求）
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # 注意：这里需要根据实际情况实现请求体读取
                body = getattr(request, '_body', b'')
                body_hash = hashlib.md5(body).hexdigest()
                key_parts.append(body_hash)
            except Exception:
                pass

        # 添加用户标识
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            key_parts.append(f"user:{user_id}")

        return ":".join(key_parts)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app):
        super().__init__(app)
        self.metrics: List[PerformanceMetrics] = []
        self._max_metrics_history = 10000

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = self._generate_request_id(request)

        try:
            response = await call_next(request)
            end_time = time.time()

            # 记录性能指标
            metrics = PerformanceMetrics(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                start_time=start_time,
                end_time=end_time,
                duration_ms=(end_time - start_time) * 1000,
                status_code=response.status_code,
                response_size=self._get_response_size(response)
            )

            self.metrics.append(metrics)
            self._cleanup_old_metrics()

            # 记录到监控系统
            self._record_metrics(metrics)

            return response

        except Exception as e:
            end_time = time.time()

            # 记录错误指标
            metrics = PerformanceMetrics(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                start_time=start_time,
                end_time=end_time,
                duration_ms=(end_time - start_time) * 1000,
                status_code=500,
                response_size=0
            )

            self.metrics.append(metrics)
            self._cleanup_old_metrics()
            self._record_metrics(metrics)

            logger.error("request_error",
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                        duration_ms=metrics.duration_ms,
                        error=str(e))

            raise

    def _generate_request_id(self, request: Request) -> str:
        """生成请求ID"""
        # 可以使用UUID或时间戳生成唯一ID
        import uuid
        return str(uuid.uuid4())

    def _get_response_size(self, response: Response) -> int:
        """获取响应大小"""
        content_length = response.headers.get("content-length")
        if content_length:
            return int(content_length)

        if hasattr(response, "body"):
            return len(response.body or b"")

        return 0

    def _cleanup_old_metrics(self):
        """清理旧的指标数据"""
        if len(self.metrics) > self._max_metrics_history:
            self.metrics = self.metrics[-self._max_metrics_history:]

    def _record_metrics(self, metrics: PerformanceMetrics):
        """记录指标到监控系统"""
        try:
            # 记录API操作指标（使用简单日志）
            if not metrics.path.startswith("/static") and metrics.path != "/health":
                logger.info(
                    "api_request",
                    method=metrics.method,
                    path=metrics.path,
                    duration_ms=round(metrics.duration_ms, 2),
                    status_code=metrics.status_code,
                    success=metrics.status_code < 400
                )

            # 记录慢请求
            if metrics.duration_ms > 1000:  # 超过1秒的请求
                logger.warning("slow_request",
                           request_id=metrics.request_id,
                           method=metrics.method,
                           path=metrics.path,
                           duration_ms=round(metrics.duration_ms, 2),
                           status_code=metrics.status_code)

        except Exception as e:
            logger.error("metrics_recording_error", error=str(e))

    def get_performance_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """获取性能统计信息"""
        import time
        from datetime import datetime, timedelta

        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [
            m for m in self.metrics
            if m.start_time >= cutoff_time
        ]

        if not recent_metrics:
            return {
                'period_minutes': minutes,
                'total_requests': 0,
                'message': 'No requests in the specified period'
            }

        # 基础统计
        total_requests = len(recent_metrics)
        successful_requests = len([m for m in recent_metrics if m.status_code < 400])
        failed_requests = total_requests - successful_requests

        # 性能统计
        durations = [m.duration_ms for m in recent_metrics]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0

        # 计算百分位数
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        p50 = sorted_durations[n // 2] if n > 0 else 0
        p95 = sorted_durations[int(n * 0.95)] if n > 0 else 0
        p99 = sorted_durations[int(n * 0.99)] if n > 0 else 0

        # 按路径分组统计
        paths_stats = {}
        for metric in recent_metrics:
            path = metric.path
            if path not in paths_stats:
                paths_stats[path] = {
                    'count': 0,
                    'total_duration': 0,
                    'max_duration': 0,
                    'status_codes': {}
                }

            stats = paths_stats[path]
            stats['count'] += 1
            stats['total_duration'] += metric.duration_ms
            stats['max_duration'] = max(stats['max_duration'], metric.duration_ms)

            status_code = metric.status_code
            if status_code not in stats['status_codes']:
                stats['status_codes'][status_code] = 0
            stats['status_codes'][status_code] += 1

        # 计算各路径的平均响应时间
        for path, stats in paths_stats.items():
            stats['avg_duration'] = stats['total_duration'] / stats['count']

        return {
            'period_minutes': minutes,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'performance': {
                'avg_duration_ms': avg_duration,
                'max_duration_ms': max_duration,
                'min_duration_ms': min_duration,
                'p50_duration_ms': p50,
                'p95_duration_ms': p95,
                'p99_duration_ms': p99
            },
            'paths_statistics': paths_stats,
            'slow_requests': [
                {
                    'path': m.path,
                    'method': m.method,
                    'duration_ms': m.duration_ms,
                    'status_code': m.status_code,
                    'request_id': m.request_id
                }
                for m in recent_metrics
                if m.duration_ms > 1000
            ]
        }


def rate_limit(max_requests: int, window_seconds: int = 60):
    """API限流装饰器"""
    def decorator(func):
        from collections import defaultdict, deque
        import time

        # 存储每个IP的请求时间
        ip_requests = defaultdict(deque)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取客户端IP（这里简化处理，实际应该从request中获取）
            client_ip = "unknown"  # 应该从request中获取

            now = time.time()
            cutoff_time = now - window_seconds

            # 清理过期请求
            while ip_requests[client_ip] and ip_requests[client_ip][0] < cutoff_time:
                ip_requests[client_ip].popleft()

            # 检查是否超过限制
            if len(ip_requests[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )

            # 记录当前请求
            ip_requests[client_ip].append(now)

            # 执行函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def async_response_cache(ttl: int = 300, key_prefix: str = "async_cache"):
    """异步响应缓存装饰器 - 暂时禁用（依赖不存在）"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 暂时直接执行，不使用缓存
            return await func(*args, **kwargs)

        return wrapper
    return decorator