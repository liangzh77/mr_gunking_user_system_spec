"""
IP 安全中间件集成测试

测试内容：
- 封禁 IP 访问拒绝
- 真实客户端 IP 提取
- 白名单路径放行
- 自动封禁流程
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.main import app
from src.services.ip_monitoring_service import BlockReason


@pytest.mark.integration
class TestIPSecurityMiddleware:
    """IP 安全中间件集成测试"""

    @pytest.mark.asyncio
    async def test_blocked_ip_access_denied(self, test_db):
        """测试被封禁 IP 访问被拒绝"""
        # 手动封禁 IP
        from src.services.ip_monitoring_service import IPMonitoringService

        async with AsyncClient(app=app, base_url="http://test") as client:
            ip_service = IPMonitoringService(test_db)
            await ip_service.block_ip_manually(
                ip_address="192.168.1.100",
                reason=BlockReason.MANUAL_BLOCK
            )

            # 模拟来自封禁 IP 的请求
            with patch("src.middleware.ip_security.IPSecurityMiddleware.get_client_ip") as mock_get_ip:
                mock_get_ip.return_value = "192.168.1.100"

                response = await client.get(
                    "/v1/admin/login",
                    headers={"X-Forwarded-For": "192.168.1.100"}
                )

                # 验证拒绝访问
                assert response.status_code == 403
                data = response.json()
                assert data["error"] == "IP_BLOCKED"
                assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_whitelist_paths_allowed(self, test_db):
        """测试白名单路径允许访问（即使 IP 被封禁）"""
        from src.services.ip_monitoring_service import IPMonitoringService

        async with AsyncClient(app=app, base_url="http://test") as client:
            ip_service = IPMonitoringService(test_db)
            await ip_service.block_ip_manually(ip_address="192.168.1.100")

            # 访问健康检查端点（白名单）
            with patch("src.middleware.ip_security.IPSecurityMiddleware.get_client_ip") as mock_get_ip:
                mock_get_ip.return_value = "192.168.1.100"

                response = await client.get("/health")

                # 验证允许访问
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_extract_ip_from_x_forwarded_for(self):
        """测试从 X-Forwarded-For 提取真实 IP"""
        from src.middleware.ip_security import IPSecurityMiddleware

        # 模拟请求
        mock_request = AsyncMock()
        mock_request.headers.get = lambda h: {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.1, 192.0.2.1",
            "X-Real-IP": None,
            "CF-Connecting-IP": None
        }.get(h)

        middleware = IPSecurityMiddleware(None)
        client_ip = middleware.get_client_ip(mock_request)

        # 应该提取第一个 IP（真实客户端）
        assert client_ip == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_extract_ip_from_x_real_ip(self):
        """测试从 X-Real-IP 提取 IP"""
        from src.middleware.ip_security import IPSecurityMiddleware

        mock_request = AsyncMock()
        mock_request.headers.get = lambda h: {
            "X-Forwarded-For": None,
            "X-Real-IP": "203.0.113.1",
            "CF-Connecting-IP": None
        }.get(h)

        middleware = IPSecurityMiddleware(None)
        client_ip = middleware.get_client_ip(mock_request)

        assert client_ip == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_extract_ip_from_cloudflare(self):
        """测试从 CF-Connecting-IP 提取 IP"""
        from src.middleware.ip_security import IPSecurityMiddleware

        mock_request = AsyncMock()
        mock_request.headers.get = lambda h: {
            "X-Forwarded-For": None,
            "X-Real-IP": None,
            "CF-Connecting-IP": "203.0.113.1"
        }.get(h)

        middleware = IPSecurityMiddleware(None)
        client_ip = middleware.get_client_ip(mock_request)

        assert client_ip == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_fallback_to_direct_ip(self):
        """测试回退到直接连接 IP"""
        from src.middleware.ip_security import IPSecurityMiddleware

        mock_request = AsyncMock()
        mock_request.headers.get = lambda h: None
        mock_request.client.host = "192.168.1.1"

        middleware = IPSecurityMiddleware(None)
        client_ip = middleware.get_client_ip(mock_request)

        assert client_ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_login_failure_auto_block(self, test_db, test_admin):
        """测试登录失败自动封禁流程"""
        from src.services.ip_monitoring_service import IPMonitoringService

        ip_service = IPMonitoringService(test_db)
        test_ip = "192.168.1.200"

        # 模拟 5 次登录失败
        for i in range(5):
            result = await ip_service.record_login_failure(
                ip_address=test_ip,
                username="admin",
                user_type="admin"
            )

            # 第 5 次应触发封禁
            if i == 4:
                assert result["blocked"] is True
                assert result["reason"] == BlockReason.BRUTE_FORCE

        # 验证 IP 已被封禁
        block_info = await ip_service.check_ip_blocked(test_ip)
        assert block_info["blocked"] is True

    @pytest.mark.asyncio
    async def test_login_success_clears_failures(self, test_db):
        """测试登录成功清除失败计数"""
        from src.services.ip_monitoring_service import IPMonitoringService

        ip_service = IPMonitoringService(test_db)
        test_ip = "192.168.1.201"

        # 记录 3 次失败
        for _ in range(3):
            await ip_service.record_login_failure(
                ip_address=test_ip,
                username="admin",
                user_type="admin"
            )

        # 登录成功
        await ip_service.record_login_success(test_ip)

        # 再次失败应从 1 开始计数
        result = await ip_service.record_login_failure(
            ip_address=test_ip,
            username="admin",
            user_type="admin"
        )
        assert result["failure_count"] == 1
        assert result["blocked"] is False

    @pytest.mark.asyncio
    async def test_ip_reputation_calculation(self, test_db):
        """测试 IP 信誉评分计算"""
        from src.services.ip_monitoring_service import IPMonitoringService, IPReputationLevel

        ip_service = IPMonitoringService(test_db)
        test_ip = "192.168.1.202"

        # 初始状态：可信
        reputation = await ip_service.calculate_ip_reputation(test_ip)
        assert reputation["level"] == IPReputationLevel.TRUSTED

        # 记录 2 次失败：20 分 = 正常
        for _ in range(2):
            await ip_service.record_login_failure(test_ip, "admin", "admin")

        reputation = await ip_service.calculate_ip_reputation(test_ip)
        assert reputation["score"] == 20
        assert reputation["level"] == IPReputationLevel.NORMAL

        # 记录 3 次失败：30 分 = 可疑
        await ip_service.record_login_failure(test_ip, "admin", "admin")
        reputation = await ip_service.calculate_ip_reputation(test_ip)
        assert reputation["score"] == 30
        assert reputation["level"] == IPReputationLevel.SUSPICIOUS
