"""余额不足定时检查任务 (T220)

定时任务：每小时检查所有运营商的余额
如果余额低于阈值（100元），自动发送提醒通知
"""

import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operator import OperatorAccount
from ..models.message import OperatorMessage
from ..services.notification import NotificationService
from ..db.session import get_async_session
from ..core import get_logger

logger = get_logger(__name__)

# 余额预警阈值
BALANCE_THRESHOLD = Decimal("100.00")

# 消息发送冷却期（避免重复发送）
COOLDOWN_HOURS = 24


async def check_low_balance_and_notify():
    """检查余额不足并发送通知

    逻辑：
    1. 查询所有余额低于阈值的运营商
    2. 检查是否在冷却期内（24小时内是否已发送过余额提醒）
    3. 发送余额不足提醒通知
    """
    async with get_async_session() as db:
        try:
            # 查询余额低于阈值的运营商
            result = await db.execute(
                select(OperatorAccount)
                .where(
                    OperatorAccount.balance < BALANCE_THRESHOLD,
                    OperatorAccount.is_active == True
                )
            )
            operators = result.scalars().all()

            if not operators:
                logger.info("balance_check_no_alerts", message="没有需要提醒的运营商")
                return

            notification_service = NotificationService(db)
            notified_count = 0

            for operator in operators:
                # 检查是否在冷却期内（24小时内是否已发送过余额不足提醒）
                cooldown_time = datetime.now(timezone.utc) - timedelta(hours=COOLDOWN_HOURS)

                recent_alert_result = await db.execute(
                    select(OperatorMessage)
                    .where(
                        OperatorMessage.operator_id == operator.id,
                        OperatorMessage.message_type == "balance_low",
                        OperatorMessage.created_at > cooldown_time
                    )
                    .limit(1)
                )
                recent_alert = recent_alert_result.scalar_one_or_none()

                if recent_alert:
                    logger.debug(
                        "balance_check_skip_cooldown",
                        operator_id=str(operator.id),
                        balance=float(operator.balance),
                        message=f"跳过（冷却期内）：{operator.full_name}"
                    )
                    continue

                # 发送余额不足提醒
                try:
                    await notification_service.send_balance_low_alert(
                        operator_id=operator.id,
                        current_balance=operator.balance,
                        threshold=BALANCE_THRESHOLD
                    )
                    notified_count += 1
                    logger.info(
                        "balance_check_alert_sent",
                        operator_id=str(operator.id),
                        operator_name=operator.full_name,
                        balance=float(operator.balance),
                        message=f"已发送余额不足提醒"
                    )
                except Exception as e:
                    logger.error(
                        "balance_check_alert_failed",
                        operator_id=str(operator.id),
                        error=str(e),
                        message=f"发送余额提醒失败"
                    )

            await db.commit()

            logger.info(
                "balance_check_completed",
                total_low_balance=len(operators),
                notified_count=notified_count,
                message=f"余额检查完成：{len(operators)}个低余额账户，发送{notified_count}条提醒"
            )

        except Exception as e:
            logger.error(
                "balance_check_error",
                error=str(e),
                message="余额检查任务执行失败"
            )
            await db.rollback()
            raise


async def run_balance_check_task():
    """运行余额检查任务（可被调度器调用）"""
    logger.info("balance_check_started", message="开始执行余额检查任务")
    await check_low_balance_and_notify()


if __name__ == "__main__":
    # 用于测试或手动执行
    asyncio.run(run_balance_check_task())
