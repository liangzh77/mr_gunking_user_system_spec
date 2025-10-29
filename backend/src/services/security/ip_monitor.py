"""异常IP检测服务 (T278, FR-056)

实现两种检测规则：
1. 单IP 5分钟内失败>20次 → 锁定账户
2. 单IP 1分钟内使用不同API Key>5个 → 锁定账户

触发后自动锁定关联账户并发送告警邮件给管理员。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Set, List
from collections import defaultdict, deque
from uuid import UUID as PyUUID
import threading

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.operator import OperatorAccount
from ...models.admin import AdminAccount


class IPActivityTracker:
    """IP活动跟踪器（内存存储）

    使用deque存储时间戳，自动清理过期数据。
    """

    def __init__(self):
        """初始化跟踪器"""
        # {ip: deque([timestamp1, timestamp2, ...])}
        self.failure_timestamps: Dict[str, deque] = defaultdict(lambda: deque())

        # {ip: [(api_key, timestamp), ...]}
        self.api_key_usage: Dict[str, List[tuple]] = defaultdict(list)

        # {ip: {operator_id, ...}}  # 记录IP关联的运营商
        self.ip_operators: Dict[str, Set[PyUUID]] = defaultdict(set)

        # 线程锁
        self._lock = threading.Lock()

    def record_failure(self, ip: str, operator_id: Optional[PyUUID] = None) -> int:
        """记录失败尝试

        Args:
            ip: 客户端IP地址
            operator_id: 运营商ID（可选）

        Returns:
            int: 5分钟内的失败次数
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=5)

        with self._lock:
            # 清理5分钟前的记录
            timestamps = self.failure_timestamps[ip]
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()

            # 记录新失败
            timestamps.append(now)

            # 记录IP关联的运营商
            if operator_id:
                self.ip_operators[ip].add(operator_id)

            return len(timestamps)

    def record_api_key_usage(
        self,
        ip: str,
        api_key: str,
        operator_id: Optional[PyUUID] = None
    ) -> int:
        """记录API Key使用

        Args:
            ip: 客户端IP地址
            api_key: API Key（只存储前8位用于标识）
            operator_id: 运营商ID（可选）

        Returns:
            int: 1分钟内使用的不同API Key数量
        """
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(minutes=1)

        with self._lock:
            # 清理1分钟前的记录
            usage_list = self.api_key_usage[ip]
            self.api_key_usage[ip] = [
                (key, ts) for key, ts in usage_list if ts >= cutoff_time
            ]

            # 记录新使用（只存储API Key前8位）
            api_key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
            self.api_key_usage[ip].append((api_key_prefix, now))

            # 记录IP关联的运营商
            if operator_id:
                self.ip_operators[ip].add(operator_id)

            # 统计不同API Key数量
            unique_keys = {key for key, _ in self.api_key_usage[ip]}
            return len(unique_keys)

    def get_associated_operators(self, ip: str) -> List[PyUUID]:
        """获取IP关联的所有运营商ID

        Args:
            ip: 客户端IP地址

        Returns:
            List[PyUUID]: 运营商ID列表
        """
        with self._lock:
            return list(self.ip_operators.get(ip, set()))

    def clear_ip_records(self, ip: str):
        """清除IP的所有记录

        Args:
            ip: 客户端IP地址
        """
        with self._lock:
            self.failure_timestamps.pop(ip, None)
            self.api_key_usage.pop(ip, None)
            self.ip_operators.pop(ip, None)


class IPMonitorService:
    """异常IP检测服务

    检测异常IP行为并自动锁定关联账户。
    """

    # 全局单例跟踪器（跨请求共享）
    _tracker = IPActivityTracker()

    # 检测阈值
    FAILURE_THRESHOLD = 20  # 5分钟内失败次数阈值
    API_KEY_THRESHOLD = 5   # 1分钟内不同API Key数量阈值

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.tracker = self._tracker

    async def check_failure_rate(
        self,
        ip: str,
        operator_id: Optional[PyUUID] = None
    ) -> dict:
        """检查失败率（规则1：5分钟内失败>20次）

        Args:
            ip: 客户端IP地址
            operator_id: 运营商ID（可选）

        Returns:
            dict: {
                "is_anomaly": bool,  # 是否异常
                "failure_count": int,  # 失败次数
                "locked_operators": List[str]  # 被锁定的运营商ID列表
            }
        """
        # 记录失败
        failure_count = self.tracker.record_failure(ip, operator_id)

        # 检查是否超过阈值
        is_anomaly = failure_count > self.FAILURE_THRESHOLD
        locked_operators = []

        if is_anomaly:
            # 锁定关联的所有运营商
            operator_ids = self.tracker.get_associated_operators(ip)
            locked_operators = await self._lock_operators(
                operator_ids,
                reason=f"IP {ip} 在5分钟内失败{failure_count}次"
            )

            # 发送告警邮件
            await self._send_alert(
                ip=ip,
                rule="failure_rate",
                details=f"5分钟内失败{failure_count}次",
                locked_operators=locked_operators
            )

        return {
            "is_anomaly": is_anomaly,
            "failure_count": failure_count,
            "locked_operators": locked_operators
        }

    async def check_api_key_switching(
        self,
        ip: str,
        api_key: str,
        operator_id: Optional[PyUUID] = None
    ) -> dict:
        """检查API Key切换（规则2：1分钟内使用>5个不同API Key）

        Args:
            ip: 客户端IP地址
            api_key: API Key
            operator_id: 运营商ID（可选）

        Returns:
            dict: {
                "is_anomaly": bool,  # 是否异常
                "unique_key_count": int,  # 不同API Key数量
                "locked_operators": List[str]  # 被锁定的运营商ID列表
            }
        """
        # 记录API Key使用
        unique_key_count = self.tracker.record_api_key_usage(ip, api_key, operator_id)

        # 检查是否超过阈值
        is_anomaly = unique_key_count > self.API_KEY_THRESHOLD
        locked_operators = []

        if is_anomaly:
            # 锁定关联的所有运营商
            operator_ids = self.tracker.get_associated_operators(ip)
            locked_operators = await self._lock_operators(
                operator_ids,
                reason=f"IP {ip} 在1分钟内使用{unique_key_count}个不同API Key"
            )

            # 发送告警邮件
            await self._send_alert(
                ip=ip,
                rule="api_key_switching",
                details=f"1分钟内使用{unique_key_count}个不同API Key",
                locked_operators=locked_operators
            )

        return {
            "is_anomaly": is_anomaly,
            "unique_key_count": unique_key_count,
            "locked_operators": locked_operators
        }

    async def _lock_operators(
        self,
        operator_ids: List[PyUUID],
        reason: str
    ) -> List[str]:
        """锁定运营商账户

        Args:
            operator_ids: 运营商ID列表
            reason: 锁定原因

        Returns:
            List[str]: 成功锁定的运营商ID列表（字符串格式）
        """
        locked = []

        for operator_id in operator_ids:
            # 查询运营商
            result = await self.db.execute(
                select(OperatorAccount).where(OperatorAccount.id == operator_id)
            )
            operator = result.scalar_one_or_none()

            if operator and not operator.is_locked:
                # 锁定账户
                operator.is_locked = True
                self.db.add(operator)
                locked.append(str(operator_id))

        # 提交更改
        if locked:
            await self.db.commit()

        return locked

    async def _send_alert(
        self,
        ip: str,
        rule: str,
        details: str,
        locked_operators: List[str]
    ):
        """发送告警邮件给所有管理员

        Args:
            ip: 异常IP地址
            rule: 触发的规则名称
            details: 详细信息
            locked_operators: 被锁定的运营商ID列表
        """
        # 查询所有活跃管理员
        result = await self.db.execute(
            select(AdminAccount).where(AdminAccount.is_active == True)
        )
        admins = result.scalars().all()

        # 构建告警消息
        alert_message = f"""
【安全告警】异常IP检测触发

规则: {rule}
IP地址: {ip}
详细信息: {details}
触发时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

锁定账户数: {len(locked_operators)}
锁定账户ID: {', '.join(locked_operators) if locked_operators else '无'}

请立即登录管理后台查看详情并采取必要措施。
"""

        # 这里应该调用邮件发送服务
        # 由于邮件服务可能未实现，这里只打印日志
        print(f"[SECURITY ALERT] 发送告警邮件给 {len(admins)} 位管理员")
        print(alert_message)

        # TODO: 实际生产环境应该调用邮件服务
        # await email_service.send_alert_email(
        #     recipients=[admin.email for admin in admins],
        #     subject=f"【安全告警】异常IP检测: {ip}",
        #     content=alert_message
        # )

    async def unlock_operator(self, operator_id: PyUUID) -> bool:
        """解锁运营商账户（管理员手动操作）

        Args:
            operator_id: 运营商ID

        Returns:
            bool: 是否成功解锁
        """
        result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id == operator_id)
        )
        operator = result.scalar_one_or_none()

        if not operator:
            return False

        if operator.is_locked:
            operator.is_locked = False
            self.db.add(operator)
            await self.db.commit()
            return True

        return False

    def clear_ip_tracking(self, ip: str):
        """清除IP的跟踪记录（管理员手动操作）

        Args:
            ip: IP地址
        """
        self.tracker.clear_ip_records(ip)
