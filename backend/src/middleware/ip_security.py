"""
IP 安全中间件

功能：
- 自动检查 IP 封禁状态
- 阻止被封禁的 IP 访问
- 提取真实客户端 IP（支持反向代理）
- 记录可疑访问
"""
from typing import Callable
import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core import get_settings

logger = structlog.get_logger(__name__)


class IPSecurityMiddleware(BaseHTTPMiddleware):
    """IP 安全中间件"""

    # 白名单端点（不检查封禁状态）
    WHITELIST_PATHS = [
        "/health",
        "/metrics",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json"
    ]

    def __init__(self, app):
        """
        初始化 IP 安全中间件

        Args:
            app: FastAPI 应用实例
        """
        super().__init__(app)
        self.settings = get_settings()
        self.logger = logger.bind(middleware="ip_security")

    def get_client_ip(self, request: Request) -> str:
        """
        获取真实客户端 IP 地址

        支持反向代理（Nginx、CloudFlare）

        Args:
            request: 请求对象

        Returns:
            客户端 IP 地址
        """
        # 1. 检查 X-Forwarded-For（标准代理头）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For: client, proxy1, proxy2
            # 取第一个（真实客户端 IP）
            return forwarded_for.split(",")[0].strip()

        # 2. 检查 X-Real-IP（Nginx 常用）
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # 3. 检查 CF-Connecting-IP（CloudFlare）
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()

        # 4. 回退到直接连接 IP
        return request.client.host if request.client else "unknown"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件

        Returns:
            响应对象
        """
        # 获取客户端 IP
        client_ip = self.get_client_ip(request)
        request.state.client_ip = client_ip

        # 检查是否在白名单中
        path = request.url.path
        if any(path.startswith(wp) for wp in self.WHITELIST_PATHS):
            return await call_next(request)

        # 检查 IP 是否被封禁
        from ..services.ip_monitoring_service import IPMonitoringService
        from ..core.database import get_db

        try:
            # 使用依赖注入获取数据库会话
            async for db in get_db():
                ip_service = IPMonitoringService(db)
                block_info = await ip_service.check_ip_blocked(client_ip)

                if block_info.get("blocked"):
                    self.logger.warning(
                        "blocked_ip_request_rejected",
                        ip_address=client_ip,
                        path=path,
                        reason=block_info.get("reason"),
                        expires_at=block_info.get("expires_at")
                    )

                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "IP_BLOCKED",
                            "message": "Your IP address has been blocked due to suspicious activity",
                            "reason": block_info.get("reason"),
                            "retry_after": block_info.get("remaining_seconds", 0)
                        },
                        headers={
                            "Retry-After": str(block_info.get("remaining_seconds", 3600))
                        }
                    )

                # IP 未封禁，继续处理请求
                response = await call_next(request)
                return response

        except Exception as e:
            # 如果 IP 检查失败（如 Redis 不可用），允许请求继续
            self.logger.error(
                "ip_security_check_failed",
                error=str(e),
                ip_address=client_ip
            )
            return await call_next(request)


async def get_client_ip_from_request(request: Request) -> str:
    """
    从请求中提取客户端 IP（依赖注入辅助函数）

    Args:
        request: 请求对象

    Returns:
        客户端 IP 地址
    """
    # 如果中间件已经设置了 client_ip
    if hasattr(request.state, "client_ip"):
        return request.state.client_ip

    # 否则手动提取
    middleware = IPSecurityMiddleware(None)
    return middleware.get_client_ip(request)
