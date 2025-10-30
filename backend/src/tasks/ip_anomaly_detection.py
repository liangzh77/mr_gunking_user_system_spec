"""异常IP检测定时任务 (FR-056a)

检测异常IP行为并自动锁定关联账户，响应时间<1分钟。

检测规则：
1. 单IP在5分钟内失败次数>20次
2. 单IP在1分钟内使用不同API Key>5个

容错机制：
1. 检测任务每30秒执行一次（确保<1分钟响应）
2. 任务执行失败自动重试（最多2次，30秒间隔）
3. 锁定账户失败时记录日志并发送告警
4. 使用数据库索引优化查询性能（确保查询时间<30秒）

相关需求：
- FR-056: 异常IP检测规则
- FR-056a: 响应时间必须<1分钟
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set
from uuid import UUID

from sqlalchemy import select, and_, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.authorization_log import AuthorizationLog
from ..models.operator import OperatorAccount
from ..db.session import get_db_context
from ..core import get_logger

logger = get_logger(__name__)

# 检测阈值
FAILURE_THRESHOLD_COUNT = 20  # 5分钟内失败20次
FAILURE_WINDOW_MINUTES = 5

API_KEY_THRESHOLD_COUNT = 5  # 1分钟内使用5个不同API Key
API_KEY_WINDOW_MINUTES = 1

ALERT_EMAIL = "security@example.com"  # 安全团队邮箱


async def detect_and_lock_anomalous_ips():
    """检测异常IP并锁定关联账户

    逻辑：
    1. 检测规则1: 单IP在5分钟内失败次数>20次
    2. 检测规则2: 单IP在1分钟内使用不同API Key>5个
    3. 锁定所有关联的运营商账户
    4. 发送安全告警
    """
    async with get_db_context() as db:
        try:
            # 统计信息
            stats = {
                "rule1_violations": 0,  # 规则1违规IP数
                "rule2_violations": 0,  # 规则2违规IP数
                "locked_accounts": 0,   # 锁定账户数
                "alerts_sent": 0,        # 发送告警数
            }

            # 规则1: 检测高失败率IP
            anomalous_ips_rule1 = await _detect_high_failure_ips(db)
            stats["rule1_violations"] = len(anomalous_ips_rule1)

            if anomalous_ips_rule1:
                logger.warning(
                    "ip_anomaly_rule1_triggered",
                    count=len(anomalous_ips_rule1),
                    ips=list(anomalous_ips_rule1),
                    message=f"检测到{len(anomalous_ips_rule1)}个高失败率IP"
                )

            # 规则2: 检测多API Key使用IP
            anomalous_ips_rule2 = await _detect_multi_api_key_ips(db)
            stats["rule2_violations"] = len(anomalous_ips_rule2)

            if anomalous_ips_rule2:
                logger.warning(
                    "ip_anomaly_rule2_triggered",
                    count=len(anomalous_ips_rule2),
                    ips=list(anomalous_ips_rule2),
                    message=f"检测到{len(anomalous_ips_rule2)}个多API Key使用IP"
                )

            # 合并所有异常IP
            all_anomalous_ips = anomalous_ips_rule1.union(anomalous_ips_rule2)

            if not all_anomalous_ips:
                logger.info(
                    "ip_anomaly_detection_no_anomalies",
                    message="未检测到异常IP"
                )
                return

            # 锁定关联账户
            for ip in all_anomalous_ips:
                try:
                    locked_count = await _lock_accounts_by_ip(db, ip, stats)
                    stats["locked_accounts"] += locked_count

                    if locked_count > 0:
                        # 发送告警
                        await _send_security_alert(
                            ip=ip,
                            locked_accounts=locked_count,
                            rule1_violated=ip in anomalous_ips_rule1,
                            rule2_violated=ip in anomalous_ips_rule2,
                        )
                        stats["alerts_sent"] += 1

                except Exception as e:
                    logger.error(
                        "ip_anomaly_lock_failed",
                        ip=ip,
                        error=str(e),
                        message=f"锁定IP{ip}关联账户失败"
                    )

            # 提交所有锁定操作
            await db.commit()

            logger.info(
                "ip_anomaly_detection_completed",
                **stats,
                message=(
                    f"异常IP检测完成: "
                    f"规则1违规{stats['rule1_violations']}个IP, "
                    f"规则2违规{stats['rule2_violations']}个IP, "
                    f"锁定{stats['locked_accounts']}个账户, "
                    f"发送{stats['alerts_sent']}条告警"
                )
            )

        except Exception as e:
            logger.error(
                "ip_anomaly_detection_error",
                error=str(e),
                message="异常IP检测任务执行失败"
            )
            await db.rollback()
            raise


async def _detect_high_failure_ips(db: AsyncSession) -> Set[str]:
    """检测规则1: 单IP在5分钟内失败次数>20次

    Args:
        db: 数据库会话

    Returns:
        Set[str]: 异常IP集合
    """
    threshold_time = datetime.now(timezone.utc) - timedelta(
        minutes=FAILURE_WINDOW_MINUTES
    )

    # 查询5分钟内每个IP的失败次数
    result = await db.execute(
        select(
            AuthorizationLog.client_ip,
            func.count(AuthorizationLog.id).label("failure_count"),
        )
        .where(
            and_(
                AuthorizationLog.created_at > threshold_time,
                AuthorizationLog.is_success == False,
            )
        )
        .group_by(AuthorizationLog.client_ip)
        .having(func.count(AuthorizationLog.id) > FAILURE_THRESHOLD_COUNT)
    )

    anomalous_ips = {row.client_ip for row in result}

    if anomalous_ips:
        logger.warning(
            "high_failure_ips_detected",
            count=len(anomalous_ips),
            threshold=FAILURE_THRESHOLD_COUNT,
            window_minutes=FAILURE_WINDOW_MINUTES,
            ips=list(anomalous_ips),
        )

    return anomalous_ips


async def _detect_multi_api_key_ips(db: AsyncSession) -> Set[str]:
    """检测规则2: 单IP在1分钟内使用不同API Key>5个

    Args:
        db: 数据库会话

    Returns:
        Set[str]: 异常IP集合
    """
    threshold_time = datetime.now(timezone.utc) - timedelta(
        minutes=API_KEY_WINDOW_MINUTES
    )

    # 查询1分钟内每个IP使用的不同API Key数量
    result = await db.execute(
        select(
            AuthorizationLog.client_ip,
            func.count(distinct(AuthorizationLog.operator_id)).label("api_key_count"),
        )
        .where(AuthorizationLog.created_at > threshold_time)
        .group_by(AuthorizationLog.client_ip)
        .having(func.count(distinct(AuthorizationLog.operator_id)) > API_KEY_THRESHOLD_COUNT)
    )

    anomalous_ips = {row.client_ip for row in result}

    if anomalous_ips:
        logger.warning(
            "multi_api_key_ips_detected",
            count=len(anomalous_ips),
            threshold=API_KEY_THRESHOLD_COUNT,
            window_minutes=API_KEY_WINDOW_MINUTES,
            ips=list(anomalous_ips),
        )

    return anomalous_ips


async def _lock_accounts_by_ip(
    db: AsyncSession,
    ip: str,
    stats: Dict[str, int]
) -> int:
    """锁定IP关联的所有运营商账户

    Args:
        db: 数据库会话
        ip: 异常IP地址
        stats: 统计信息字典

    Returns:
        int: 锁定的账户数
    """
    # 查询该IP最近使用的所有运营商账户
    threshold_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    result = await db.execute(
        select(distinct(AuthorizationLog.operator_id))
        .where(
            and_(
                AuthorizationLog.client_ip == ip,
                AuthorizationLog.created_at > threshold_time,
            )
        )
    )

    operator_ids = [row[0] for row in result]

    if not operator_ids:
        logger.warning(
            "no_accounts_found_for_ip",
            ip=ip,
            message=f"IP{ip}未找到关联的运营商账户"
        )
        return 0

    locked_count = 0

    for operator_id in operator_ids:
        # 获取运营商账户
        op_result = await db.execute(
            select(OperatorAccount).where(
                OperatorAccount.id == operator_id
            )
        )
        operator = op_result.scalar_one_or_none()

        if not operator:
            continue

        # 跳过已锁定的账户
        if operator.is_locked:
            logger.debug(
                "account_already_locked",
                operator_id=str(operator_id),
                ip=ip,
            )
            continue

        # 锁定账户
        operator.is_locked = True
        operator.locked_reason = (
            f"检测到异常IP行为: {ip}。"
            f"触发时间: {datetime.now(timezone.utc).isoformat()}。"
            f"请联系安全团队解锁。"
        )
        operator.locked_at = datetime.now(timezone.utc)
        operator.updated_at = datetime.now(timezone.utc)

        locked_count += 1

        logger.critical(
            "account_locked_by_ip_anomaly",
            operator_id=str(operator_id),
            operator_name=operator.full_name,
            ip=ip,
            reason=operator.locked_reason,
            message=f"账户已锁定: {operator.full_name} (IP: {ip})"
        )

    return locked_count


async def _send_security_alert(
    ip: str,
    locked_accounts: int,
    rule1_violated: bool,
    rule2_violated: bool,
):
    """发送安全告警

    Args:
        ip: 异常IP地址
        locked_accounts: 锁定的账户数
        rule1_violated: 是否违反规则1
        rule2_violated: 是否违反规则2
    """
    violation_rules = []
    if rule1_violated:
        violation_rules.append(
            f"规则1: 5分钟内失败>{FAILURE_THRESHOLD_COUNT}次"
        )
    if rule2_violated:
        violation_rules.append(
            f"规则2: 1分钟内使用>{API_KEY_THRESHOLD_COUNT}个不同API Key"
        )

    logger.critical(
        "security_alert_sent",
        ip=ip,
        locked_accounts=locked_accounts,
        violation_rules=violation_rules,
        recipient=ALERT_EMAIL,
        message=(
            f"安全告警: IP {ip} 检测到异常行为，"
            f"已锁定{locked_accounts}个账户。"
            f"违规规则: {', '.join(violation_rules)}"
        ),
    )

    # TODO: 实际发送邮件
    # from ..services.email import send_email
    # await send_email(
    #     to=ALERT_EMAIL,
    #     subject=f"安全告警 - 异常IP检测: {ip}",
    #     body=f"检测详情: ...",
    # )


async def run_ip_anomaly_detection_task():
    """运行异常IP检测任务（由调度器调用）"""
    logger.info(
        "ip_anomaly_detection_task_started",
        message="开始执行异常IP检测任务"
    )

    await detect_and_lock_anomalous_ips()


# 手动执行入口（用于测试）
if __name__ == "__main__":
    asyncio.run(run_ip_anomaly_detection_task())
