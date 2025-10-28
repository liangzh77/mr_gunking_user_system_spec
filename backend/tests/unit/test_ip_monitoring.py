"""
IP 监控服务单元测试

测试内容：
- 登录失败记录
- 自动封禁机制
- IP 解封
- 信誉评分计算
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.services.ip_monitoring_service import (
    IPMonitoringService,
    BlockReason,
    IPReputationLevel
)


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return AsyncMock()


@pytest.fixture
def mock_cache():
    """模拟缓存"""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.get_by_pattern = AsyncMock(return_value=[])
    return cache


@pytest.fixture
def ip_service(mock_db, mock_cache, monkeypatch):
    """创建 IP 监控服务实例"""
    service = IPMonitoringService(mock_db)

    # 替换 get_cache()
    def mock_get_cache():
        return mock_cache
    monkeypatch.setattr("src.services.ip_monitoring_service.get_cache", mock_get_cache)
    service.cache = mock_cache

    return service


@pytest.mark.unit
class TestIPMonitoring:
    """IP 监控服务测试"""

    @pytest.mark.asyncio
    async def test_record_login_failure_first_time(self, ip_service, mock_cache):
        """测试首次登录失败记录"""
        # 模拟首次失败（缓存为空）
        mock_cache.get = AsyncMock(return_value=None)

        result = await ip_service.record_login_failure(
            ip_address="192.168.1.100",
            username="admin",
            user_type="admin"
        )

        # 验证结果
        assert result["blocked"] is False
        assert result["failure_count"] == 1
        assert result["remaining_attempts"] == 4

        # 验证缓存调用
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert "login_failures:192.168.1.100" in call_args[0]

    @pytest.mark.asyncio
    async def test_record_login_failure_triggers_block(self, ip_service, mock_cache):
        """测试登录失败达到阈值触发封禁"""
        from src.core import get_current_timestamp
        current_time = get_current_timestamp()

        # 模拟已有 4 次失败（在窗口期内）
        existing_failures = [
            {"timestamp": current_time - 100 - i, "username": "admin", "user_type": "admin"}
            for i in range(4)
        ]
        mock_cache.get = AsyncMock(return_value=existing_failures)

        # 第 5 次失败
        result = await ip_service.record_login_failure(
            ip_address="192.168.1.100",
            username="admin",
            user_type="admin"
        )

        # 验证自动封禁
        assert result["blocked"] is True
        assert result["reason"] == BlockReason.BRUTE_FORCE
        assert result["failure_count"] == 5
        assert result["duration"] == ip_service.AUTO_BLOCK_DURATION

        # 验证封禁信息已存入缓存
        assert mock_cache.set.call_count >= 2  # 失败记录 + 封禁记录

    @pytest.mark.asyncio
    async def test_record_login_success_clears_failures(self, ip_service, mock_cache):
        """测试登录成功清除失败计数"""
        await ip_service.record_login_success("192.168.1.100")

        # 验证删除缓存
        mock_cache.delete.assert_called_once_with("login_failures:192.168.1.100")

    @pytest.mark.asyncio
    async def test_check_ip_blocked_returns_block_info(self, ip_service, mock_cache):
        """测试检查被封禁 IP"""
        from src.core import get_current_timestamp
        current_time = get_current_timestamp()

        # 模拟封禁信息
        block_info = {
            "ip_address": "192.168.1.100",
            "reason": BlockReason.BRUTE_FORCE,
            "blocked_at": current_time - 1000,
            "expires_at": current_time + 3600,  # 1小时后
            "auto_blocked": True
        }
        mock_cache.get = AsyncMock(return_value=block_info)

        result = await ip_service.check_ip_blocked("192.168.1.100")

        # 验证返回封禁状态
        assert result["blocked"] is True
        assert result["reason"] == BlockReason.BRUTE_FORCE
        assert "remaining_seconds" in result

    @pytest.mark.asyncio
    async def test_check_ip_not_blocked(self, ip_service, mock_cache):
        """测试检查未封禁 IP"""
        mock_cache.get = AsyncMock(return_value=None)

        result = await ip_service.check_ip_blocked("192.168.1.100")

        assert result["blocked"] is False

    @pytest.mark.asyncio
    async def test_block_ip_manually(self, ip_service, mock_cache):
        """测试手动封禁 IP"""
        result = await ip_service.block_ip_manually(
            ip_address="192.168.1.100",
            reason=BlockReason.MANUAL_BLOCK,
            admin_id="admin-123"
        )

        # 验证封禁信息
        assert result["ip_address"] == "192.168.1.100"
        assert result["reason"] == BlockReason.MANUAL_BLOCK
        assert result["auto_blocked"] is False
        assert result["admin_id"] == "admin-123"

        # 验证缓存调用
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_unblock_ip(self, ip_service, mock_cache):
        """测试解封 IP"""
        result = await ip_service.unblock_ip(
            ip_address="192.168.1.100",
            admin_id="admin-123"
        )

        assert result is True

        # 验证删除两个缓存键
        assert mock_cache.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_calculate_ip_reputation_trusted(self, ip_service, mock_cache):
        """测试计算可信 IP 信誉"""
        mock_cache.get = AsyncMock(return_value=None)

        result = await ip_service.calculate_ip_reputation("192.168.1.100")

        assert result["score"] == 0
        assert result["level"] == IPReputationLevel.TRUSTED

    @pytest.mark.asyncio
    async def test_calculate_ip_reputation_suspicious(self, ip_service, mock_cache):
        """测试计算可疑 IP 信誉"""
        # 模拟 3 次登录失败
        failures = [{"timestamp": 1000000 + i} for i in range(3)]

        async def mock_get(key):
            if "login_failures" in key:
                return failures
            if "blocked_ip" in key:
                return None
            if "block_history" in key:
                return []
            return None

        mock_cache.get = AsyncMock(side_effect=mock_get)

        result = await ip_service.calculate_ip_reputation("192.168.1.100")

        # 3 次失败 = 30 分
        assert result["score"] == 30
        assert result["level"] == IPReputationLevel.SUSPICIOUS
        assert result["failure_count"] == 3

    @pytest.mark.asyncio
    async def test_get_blocked_ips(self, ip_service, mock_cache):
        """测试获取所有被封禁 IP"""
        from src.core import get_current_timestamp
        current_time = get_current_timestamp()

        # 模拟两个封禁 IP
        blocked_ips = [
            {
                "ip_address": "192.168.1.100",
                "expires_at": current_time + 3600,  # 未过期
                "reason": BlockReason.BRUTE_FORCE
            },
            {
                "ip_address": "192.168.1.101",
                "expires_at": current_time - 1000,  # 已过期
                "reason": BlockReason.MANUAL_BLOCK
            }
        ]
        mock_cache.get_by_pattern = AsyncMock(return_value=blocked_ips)

        result = await ip_service.get_blocked_ips()

        # 只返回未过期的
        assert len(result) == 1
        assert result[0]["ip_address"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_record_sensitive_access(self, ip_service, mock_cache):
        """测试记录敏感端点访问"""
        mock_cache.get = AsyncMock(return_value=[])

        await ip_service.record_sensitive_access(
            ip_address="192.168.1.100",
            endpoint="/v1/admin/users",
            user_id="admin-123"
        )

        # 验证缓存调用
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert "sensitive_access:192.168.1.100" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_ip_statistics(self, ip_service, mock_cache):
        """测试获取 IP 统计信息"""
        # 模拟数据
        failures = [{"timestamp": 1000000}]
        sensitive_accesses = [{"timestamp": 1000001, "endpoint": "/admin"}]
        block_info = {"blocked": False}

        async def mock_get(key):
            if "login_failures" in key:
                return failures
            if "sensitive_access" in key:
                return sensitive_accesses
            return []

        mock_cache.get = AsyncMock(side_effect=mock_get)

        # 模拟 check_ip_blocked
        async def mock_check_ip_blocked(ip):
            return block_info
        ip_service.check_ip_blocked = AsyncMock(side_effect=mock_check_ip_blocked)

        # 模拟 calculate_ip_reputation
        async def mock_calculate_reputation(ip):
            return {"score": 10, "level": IPReputationLevel.NORMAL}
        ip_service.calculate_ip_reputation = AsyncMock(side_effect=mock_calculate_reputation)

        result = await ip_service.get_ip_statistics("192.168.1.100")

        # 验证统计信息
        assert result["ip_address"] == "192.168.1.100"
        assert result["login_failures"] == 1
        assert result["sensitive_accesses"] == 1
        assert result["blocked"] is False
        assert result["reputation"]["score"] == 10
