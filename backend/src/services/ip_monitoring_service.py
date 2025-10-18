"""
IP 监控和异常检测服务

功能：
- 登录失败次数监控（暴力破解检测）
- IP 黑名单管理（手动/自动封禁）
- 异常行为检测（频繁访问敏感端点）
- 自动解封机制（基于时间的临时封禁）
- IP 信誉评分系统
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import structlog
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_cache, get_current_timestamp
from ..models.operator import OperatorAccount
from ..models.admin import AdminAccount

logger = structlog.get_logger(__name__)


class BlockReason(str, Enum):
    """IP 封禁原因"""
    BRUTE_FORCE = "brute_force"  # 暴力破解
    SUSPICIOUS_ACTIVITY = "suspicious_activity"  # 可疑活动
    MANUAL_BLOCK = "manual_block"  # 手动封禁
    RATE_LIMIT_ABUSE = "rate_limit_abuse"  # 频率滥用


class IPReputationLevel(str, Enum):
    """IP 信誉等级"""
    TRUSTED = "trusted"  # 可信（0-20分）
    NORMAL = "normal"  # 正常（21-50分）
    SUSPICIOUS = "suspicious"  # 可疑（51-80分）
    MALICIOUS = "malicious"  # 恶意（81-100分）
    BLOCKED = "blocked"  # 已封禁


class IPMonitoringService:
    """IP 监控服务"""

    # 配置常量
    MAX_LOGIN_FAILURES = 5  # 最大登录失败次数
    LOGIN_FAILURE_WINDOW = 900  # 登录失败窗口期（15分钟）
    AUTO_BLOCK_DURATION = 3600  # 自动封禁时长（1小时）
    MANUAL_BLOCK_DURATION = 86400  # 手动封禁时长（24小时）
    PERMANENT_BLOCK_DURATION = 31536000  # 永久封禁（1年）

    def __init__(self, db: AsyncSession):
        """
        初始化 IP 监控服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.cache = get_cache()
        self.logger = logger.bind(service="ip_monitoring")

    async def record_login_failure(
        self,
        ip_address: str,
        username: Optional[str] = None,
        user_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录登录失败事件

        Args:
            ip_address: IP 地址
            username: 尝试登录的用户名
            user_type: 用户类型（admin/operator）

        Returns:
            包含警告信息的字典
        """
        cache_key = f"login_failures:{ip_address}"
        current_time = get_current_timestamp()

        # 获取当前失败记录
        failures = await self.cache.get(cache_key) or []

        # 添加新失败记录
        failures.append({
            "timestamp": current_time,
            "username": username,
            "user_type": user_type
        })

        # 过滤掉窗口期外的记录
        cutoff_time = current_time - self.LOGIN_FAILURE_WINDOW
        recent_failures = [
            f for f in failures
            if f["timestamp"] > cutoff_time
        ]

        # 更新缓存（窗口期 + 1小时）
        await self.cache.set(
            cache_key,
            recent_failures,
            ttl=self.LOGIN_FAILURE_WINDOW + 3600
        )

        failure_count = len(recent_failures)

        self.logger.warning(
            "login_failure_recorded",
            ip_address=ip_address,
            username=username,
            user_type=user_type,
            failure_count=failure_count
        )

        # 检查是否触发自动封禁
        if failure_count >= self.MAX_LOGIN_FAILURES:
            await self._auto_block_ip(ip_address, recent_failures)
            return {
                "blocked": True,
                "reason": BlockReason.BRUTE_FORCE,
                "failure_count": failure_count,
                "duration": self.AUTO_BLOCK_DURATION
            }

        return {
            "blocked": False,
            "failure_count": failure_count,
            "remaining_attempts": self.MAX_LOGIN_FAILURES - failure_count
        }

    async def record_login_success(self, ip_address: str) -> None:
        """
        记录登录成功事件（清除失败计数）

        Args:
            ip_address: IP 地址
        """
        cache_key = f"login_failures:{ip_address}"
        await self.cache.delete(cache_key)

        self.logger.info(
            "login_success_recorded",
            ip_address=ip_address
        )

    async def _auto_block_ip(
        self,
        ip_address: str,
        failures: List[Dict[str, Any]]
    ) -> None:
        """
        自动封禁 IP（内部方法）

        Args:
            ip_address: IP 地址
            failures: 失败记录列表
        """
        block_key = f"blocked_ip:{ip_address}"
        current_time = get_current_timestamp()

        # 分析失败模式
        usernames = list(set(f.get("username") for f in failures if f.get("username")))

        block_info = {
            "ip_address": ip_address,
            "reason": BlockReason.BRUTE_FORCE,
            "blocked_at": current_time,
            "expires_at": current_time + self.AUTO_BLOCK_DURATION,
            "failure_count": len(failures),
            "attempted_usernames": usernames,
            "auto_blocked": True
        }

        # 保存到缓存
        await self.cache.set(
            block_key,
            block_info,
            ttl=self.AUTO_BLOCK_DURATION
        )

        self.logger.warning(
            "ip_auto_blocked",
            ip_address=ip_address,
            failure_count=len(failures),
            duration=self.AUTO_BLOCK_DURATION,
            usernames=usernames
        )

    async def check_ip_blocked(self, ip_address: str) -> Dict[str, Any]:
        """
        检查 IP 是否被封禁

        Args:
            ip_address: IP 地址

        Returns:
            封禁状态信息
        """
        block_key = f"blocked_ip:{ip_address}"
        block_info = await self.cache.get(block_key)

        if not block_info:
            return {"blocked": False}

        current_time = get_current_timestamp()
        expires_at = block_info.get("expires_at", 0)

        # 检查是否已过期
        if current_time > expires_at:
            await self.cache.delete(block_key)
            self.logger.info(
                "ip_block_expired",
                ip_address=ip_address
            )
            return {"blocked": False}

        return {
            "blocked": True,
            "reason": block_info.get("reason"),
            "blocked_at": block_info.get("blocked_at"),
            "expires_at": expires_at,
            "remaining_seconds": expires_at - current_time
        }

    async def block_ip_manually(
        self,
        ip_address: str,
        reason: str = BlockReason.MANUAL_BLOCK,
        duration: Optional[int] = None,
        admin_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        手动封禁 IP

        Args:
            ip_address: IP 地址
            reason: 封禁原因
            duration: 封禁时长（秒），None 表示使用默认时长
            admin_id: 操作管理员 ID

        Returns:
            封禁信息
        """
        block_key = f"blocked_ip:{ip_address}"
        current_time = get_current_timestamp()

        if duration is None:
            duration = self.MANUAL_BLOCK_DURATION

        block_info = {
            "ip_address": ip_address,
            "reason": reason,
            "blocked_at": current_time,
            "expires_at": current_time + duration,
            "auto_blocked": False,
            "admin_id": admin_id
        }

        await self.cache.set(block_key, block_info, ttl=duration)

        self.logger.warning(
            "ip_manually_blocked",
            ip_address=ip_address,
            reason=reason,
            duration=duration,
            admin_id=admin_id
        )

        return block_info

    async def unblock_ip(
        self,
        ip_address: str,
        admin_id: Optional[str] = None
    ) -> bool:
        """
        解封 IP

        Args:
            ip_address: IP 地址
            admin_id: 操作管理员 ID

        Returns:
            是否成功解封
        """
        block_key = f"blocked_ip:{ip_address}"
        login_failures_key = f"login_failures:{ip_address}"

        # 删除封禁记录和失败计数
        await self.cache.delete(block_key)
        await self.cache.delete(login_failures_key)

        self.logger.info(
            "ip_unblocked",
            ip_address=ip_address,
            admin_id=admin_id
        )

        return True

    async def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """
        获取所有被封禁的 IP 列表

        Returns:
            封禁 IP 信息列表
        """
        # 使用缓存模式匹配
        blocked_ips = await self.cache.get_by_pattern("blocked_ip:*")

        current_time = get_current_timestamp()
        active_blocks = []

        for ip_info in blocked_ips:
            if ip_info.get("expires_at", 0) > current_time:
                active_blocks.append(ip_info)

        return active_blocks

    async def calculate_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """
        计算 IP 信誉评分

        评分规则：
        - 基础分：0
        - 每次登录失败：+10
        - 被封禁过：+30
        - 频繁访问敏感端点：+20

        Args:
            ip_address: IP 地址

        Returns:
            信誉评分和等级
        """
        score = 0

        # 检查登录失败次数
        failures_key = f"login_failures:{ip_address}"
        failures = await self.cache.get(failures_key) or []
        score += len(failures) * 10

        # 检查是否被封禁
        block_info = await self.check_ip_blocked(ip_address)
        if block_info.get("blocked"):
            score += 30

        # 检查历史封禁记录
        history_key = f"block_history:{ip_address}"
        history = await self.cache.get(history_key) or []
        score += len(history) * 20

        # 确定信誉等级
        if score == 0:
            level = IPReputationLevel.TRUSTED
        elif score <= 20:
            level = IPReputationLevel.NORMAL
        elif score <= 50:
            level = IPReputationLevel.SUSPICIOUS
        elif score <= 80:
            level = IPReputationLevel.MALICIOUS
        else:
            level = IPReputationLevel.BLOCKED

        return {
            "ip_address": ip_address,
            "score": score,
            "level": level,
            "failure_count": len(failures),
            "block_history_count": len(history)
        }

    async def record_sensitive_access(
        self,
        ip_address: str,
        endpoint: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        记录敏感端点访问

        Args:
            ip_address: IP 地址
            endpoint: 端点路径
            user_id: 用户 ID（如果已认证）
        """
        cache_key = f"sensitive_access:{ip_address}"
        current_time = get_current_timestamp()

        accesses = await self.cache.get(cache_key) or []
        accesses.append({
            "timestamp": current_time,
            "endpoint": endpoint,
            "user_id": user_id
        })

        # 只保留最近1小时的记录
        cutoff_time = current_time - 3600
        recent_accesses = [
            a for a in accesses
            if a["timestamp"] > cutoff_time
        ]

        await self.cache.set(cache_key, recent_accesses, ttl=7200)

        self.logger.info(
            "sensitive_access_recorded",
            ip_address=ip_address,
            endpoint=endpoint,
            user_id=user_id,
            access_count=len(recent_accesses)
        )

    async def get_ip_statistics(self, ip_address: str) -> Dict[str, Any]:
        """
        获取 IP 统计信息

        Args:
            ip_address: IP 地址

        Returns:
            IP 统计信息
        """
        # 获取登录失败次数
        failures_key = f"login_failures:{ip_address}"
        failures = await self.cache.get(failures_key) or []

        # 获取敏感端点访问
        sensitive_key = f"sensitive_access:{ip_address}"
        sensitive_accesses = await self.cache.get(sensitive_key) or []

        # 获取封禁状态
        block_info = await self.check_ip_blocked(ip_address)

        # 计算信誉
        reputation = await self.calculate_ip_reputation(ip_address)

        return {
            "ip_address": ip_address,
            "login_failures": len(failures),
            "sensitive_accesses": len(sensitive_accesses),
            "blocked": block_info.get("blocked", False),
            "block_info": block_info if block_info.get("blocked") else None,
            "reputation": reputation
        }
