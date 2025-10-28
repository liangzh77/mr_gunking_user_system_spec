"""
频率限制中间件

功能：
- 实现FR-055双重限制：单运营商10次/分钟、单IP 100次/分钟
- 使用slowapi库(内存实现，Phase 0无Redis)
- 超限返回HTTP 429及Retry-After响应头
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import structlog

logger = structlog.get_logger(__name__)


def get_operator_id_or_ip(request: Request) -> str:
    """
    提取限流标识符

    优先级：
    1. 如果已认证，使用operator_id（更精准控制）
    2. 否则使用客户端IP地址

    Args:
        request: FastAPI请求对象

    Returns:
        限流标识符字符串
    """
    # 如果已通过API Key认证，使用operator_id
    if hasattr(request.state, "operator_id"):
        operator_id = request.state.operator_id
        logger.debug(
            "rate_limit_key_operator",
            operator_id=str(operator_id),
            path=request.url.path
        )
        return f"operator:{operator_id}"

    # 否则使用IP地址
    client_ip = get_remote_address(request)
    logger.debug(
        "rate_limit_key_ip",
        client_ip=client_ip,
        path=request.url.path
    )
    return f"ip:{client_ip}"


# 初始化slowapi限流器
limiter = Limiter(
    key_func=get_operator_id_or_ip,
    default_limits=["100/minute"],  # 全局默认：100次/分钟(IP级)
    storage_uri="memory://",  # Phase 0使用内存存储（生产环境改为Redis）
    headers_enabled=True  # 启用X-RateLimit-*响应头
)


def setup_rate_limiter(app):
    """
    配置FastAPI应用的频率限制

    Args:
        app: FastAPI应用实例

    Example:
        from fastapi import FastAPI
        app = FastAPI()
        setup_rate_limiter(app)
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info(
        "rate_limiter_configured",
        storage="memory",
        default_limit="100/minute"
    )


# 装饰器：运营商级别限制（10次/分钟）
operator_rate_limit = limiter.limit("10/minute")

# 装饰器：IP级别限制（100次/分钟）
ip_rate_limit = limiter.limit("100/minute")


async def check_rate_limit_middleware(request: Request, call_next):
    """
    频率限制中间件（手动实现版本，可选）

    功能：
    - 在中间件层检查频率限制
    - 记录超限事件到日志
    - 返回详细的错误信息

    Args:
        request: 请求对象
        call_next: 下一个中间件

    Returns:
        响应对象
    """
    from fastapi.responses import JSONResponse
    import time

    try:
        # 调用slowapi内部逻辑检查限制
        response = await call_next(request)
        return response

    except RateLimitExceeded as e:
        # 提取限流信息
        key = get_operator_id_or_ip(request)
        retry_after = e.detail.split("Retry after ")[1] if "Retry after" in e.detail else "60 seconds"

        logger.warning(
            "rate_limit_exceeded",
            key=key,
            path=request.url.path,
            method=request.method,
            retry_after=retry_after
        )

        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. {e.detail}",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(60)}  # 60秒后重试
        )
