"""支付对账定时任务 (FR-008a)

每5分钟扫描"处理中"状态的充值订单，主动调用支付平台API查询订单状态并更新充值记录。

容错机制：
1. 单个订单查询失败不影响其他订单
2. 支付平台API连续失败3次（15分钟）标记订单为"异常"状态
3. 异常订单触发人工审核工作流（发送告警邮件给财务团队）
4. 任务执行失败自动重试（最多3次，指数退避）

相关需求：
- FR-008a: 定时对账任务规格
- Assumption: 支付回调30秒内到达，超时5分钟后主动查询
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.transaction import TransactionRecord, TransactionStatus, TransactionType
from ..models.operator import OperatorAccount
from ..db.session import get_db_context
from ..core import get_logger

logger = get_logger(__name__)

# 订单状态查询阈值
RECONCILIATION_THRESHOLD_MINUTES = 5  # 充值订单处理中超过5分钟则查询
MAX_QUERY_FAILURES = 3  # 连续查询失败3次标记为异常
ANOMALY_NOTIFICATION_EMAIL = "finance@example.com"  # 财务团队邮箱


async def reconcile_pending_payments():
    """对账主函数 - 查询所有处理中的充值订单

    逻辑：
    1. 查询所有状态为"processing"且创建时间>5分钟的充值订单
    2. 逐个调用支付平台API查询实际状态
    3. 根据查询结果更新订单状态和运营商余额
    4. 记录查询失败次数，连续失败3次标记为异常
    """
    async with get_db_context() as db:
        try:
            threshold_time = datetime.now(timezone.utc) - timedelta(
                minutes=RECONCILIATION_THRESHOLD_MINUTES
            )

            # 查询处理中的充值订单
            result = await db.execute(
                select(TransactionRecord)
                .where(
                    and_(
                        TransactionRecord.transaction_type == TransactionType.RECHARGE,
                        TransactionRecord.status == TransactionStatus.PROCESSING,
                        TransactionRecord.created_at < threshold_time,
                    )
                )
                .order_by(TransactionRecord.created_at)
            )

            pending_orders = result.scalars().all()

            if not pending_orders:
                logger.info(
                    "payment_reconciliation_no_pending",
                    message="没有需要对账的充值订单"
                )
                return

            logger.info(
                "payment_reconciliation_started",
                pending_count=len(pending_orders),
                message=f"开始对账：{len(pending_orders)}笔充值订单"
            )

            # 统计信息
            stats = {
                "total": len(pending_orders),
                "success": 0,
                "failed": 0,
                "timeout": 0,
                "anomaly": 0,
            }

            # 逐个查询订单状态
            for order in pending_orders:
                try:
                    await _reconcile_single_order(db, order, stats)
                except Exception as e:
                    logger.error(
                        "payment_reconciliation_order_error",
                        order_id=str(order.id),
                        error=str(e),
                        message=f"订单{order.id}对账失败"
                    )
                    stats["failed"] += 1

            # 提交所有更新
            await db.commit()

            logger.info(
                "payment_reconciliation_completed",
                **stats,
                message=(
                    f"对账完成: 总计{stats['total']}笔, "
                    f"成功{stats['success']}笔, "
                    f"失败{stats['failed']}笔, "
                    f"超时{stats['timeout']}笔, "
                    f"异常{stats['anomaly']}笔"
                )
            )

        except Exception as e:
            logger.error(
                "payment_reconciliation_error",
                error=str(e),
                message="支付对账任务执行失败"
            )
            await db.rollback()
            raise


async def _reconcile_single_order(
    db: AsyncSession,
    order: TransactionRecord,
    stats: Dict[str, int]
):
    """对账单个订单

    Args:
        db: 数据库会话
        order: 充值订单记录
        stats: 统计信息字典
    """
    logger.info(
        "payment_reconciliation_query_order",
        order_id=str(order.id),
        platform=order.payment_channel,
        platform_order_id=order.platform_order_id,
        amount=float(order.amount),
        created_at=order.created_at.isoformat(),
    )

    # 调用支付平台API查询订单状态
    try:
        payment_status = await _query_payment_platform(
            platform=order.payment_channel,
            platform_order_id=order.platform_order_id,
        )

        if payment_status["status"] == "success":
            # 支付成功，更新订单状态和运营商余额
            await _update_order_success(db, order)
            stats["success"] += 1

            logger.info(
                "payment_reconciliation_order_success",
                order_id=str(order.id),
                amount=float(order.amount),
                message="充值订单对账成功，已更新余额"
            )

        elif payment_status["status"] == "failed":
            # 支付失败，标记订单失败
            order.status = TransactionStatus.FAILED
            order.failure_reason = payment_status.get("reason", "支付失败")
            order.updated_at = datetime.now(timezone.utc)

            stats["failed"] += 1

            logger.warning(
                "payment_reconciliation_order_failed",
                order_id=str(order.id),
                reason=order.failure_reason,
                message="充值订单支付失败"
            )

        elif payment_status["status"] == "processing":
            # 仍在处理中，更新查询失败计数
            await _update_query_failure_count(db, order, stats)

        elif payment_status["status"] == "timeout":
            # 查询超时
            await _update_query_failure_count(db, order, stats)
            stats["timeout"] += 1

    except Exception as e:
        # 查询API异常
        logger.error(
            "payment_platform_query_error",
            order_id=str(order.id),
            platform=order.payment_channel,
            error=str(e),
            message="支付平台查询失败"
        )

        await _update_query_failure_count(db, order, stats)
        raise


async def _query_payment_platform(
    platform: str,
    platform_order_id: str
) -> Dict[str, Any]:
    """查询支付平台订单状态

    Args:
        platform: 支付平台 (wechat/alipay)
        platform_order_id: 平台订单号

    Returns:
        dict: 订单状态信息
            - status: success/failed/processing/timeout
            - reason: 失败原因(可选)
            - paid_amount: 实际支付金额(可选)
            - paid_at: 支付时间(可选)
    """
    # TODO: 实际集成微信支付/支付宝查询API
    # 目前返回模拟数据

    logger.info(
        "payment_platform_query_started",
        platform=platform,
        platform_order_id=platform_order_id,
        message=f"查询{platform}订单状态: {platform_order_id}"
    )

    # 模拟API调用延迟
    await asyncio.sleep(0.1)

    # 模拟返回（实际应调用真实API）
    # 微信支付: https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_4_2.shtml
    # 支付宝: https://opendocs.alipay.com/open/028r8t

    # 示例返回
    return {
        "status": "processing",  # 仍在处理中
        "message": "订单处理中",
    }


async def _update_order_success(db: AsyncSession, order: TransactionRecord):
    """更新订单为成功状态并增加运营商余额

    Args:
        db: 数据库会话
        order: 充值订单记录
    """
    # 获取运营商账户
    operator_result = await db.execute(
        select(OperatorAccount).where(
            OperatorAccount.id == UUID(order.related_id)
        )
    )
    operator = operator_result.scalar_one_or_none()

    if not operator:
        raise ValueError(f"运营商不存在: {order.related_id}")

    # 更新订单状态
    order.status = TransactionStatus.SUCCESS
    order.updated_at = datetime.now(timezone.utc)
    order.completed_at = datetime.now(timezone.utc)

    # 增加运营商余额
    operator.balance += order.amount
    operator.updated_at = datetime.now(timezone.utc)

    logger.info(
        "operator_balance_updated",
        operator_id=str(operator.id),
        old_balance=float(operator.balance - order.amount),
        new_balance=float(operator.balance),
        recharge_amount=float(order.amount),
        message="对账成功，已更新余额"
    )


async def _update_query_failure_count(
    db: AsyncSession,
    order: TransactionRecord,
    stats: Dict[str, int]
):
    """更新订单查询失败计数

    连续失败3次（15分钟）标记为异常状态并触发告警

    Args:
        db: 数据库会话
        order: 充值订单记录
        stats: 统计信息字典
    """
    # 初始化查询失败次数字段（如果不存在）
    if not hasattr(order, "query_failure_count"):
        order.query_failure_count = 0

    order.query_failure_count += 1
    order.updated_at = datetime.now(timezone.utc)

    logger.warning(
        "payment_query_failure_count_updated",
        order_id=str(order.id),
        failure_count=order.query_failure_count,
        max_failures=MAX_QUERY_FAILURES,
    )

    # 连续失败达到阈值，标记为异常
    if order.query_failure_count >= MAX_QUERY_FAILURES:
        order.status = TransactionStatus.FAILED
        order.failure_reason = (
            f"支付平台查询连续失败{MAX_QUERY_FAILURES}次，"
            f"需要人工审核"
        )

        stats["anomaly"] += 1

        # 发送告警
        await _send_anomaly_alert(order)

        logger.critical(
            "payment_order_marked_anomaly",
            order_id=str(order.id),
            failure_count=order.query_failure_count,
            message="充值订单标记为异常，已触发告警"
        )


async def _send_anomaly_alert(order: TransactionRecord):
    """发送异常订单告警

    通知财务团队进行人工审核

    Args:
        order: 异常订单记录
    """
    logger.critical(
        "payment_anomaly_alert_sent",
        order_id=str(order.id),
        operator_id=order.related_id,
        amount=float(order.amount),
        platform=order.payment_channel,
        platform_order_id=order.platform_order_id,
        created_at=order.created_at.isoformat(),
        recipient=ANOMALY_NOTIFICATION_EMAIL,
        message=(
            f"充值订单异常告警: 订单{order.id}查询失败{MAX_QUERY_FAILURES}次，"
            f"金额{order.amount}元，请财务人员介入处理"
        ),
    )

    # TODO: 实际发送邮件
    # from ..services.email import send_email
    # await send_email(
    #     to=ANOMALY_NOTIFICATION_EMAIL,
    #     subject=f"充值订单异常告警 - {order.id}",
    #     body=f"订单详情: ...",
    # )


async def run_payment_reconciliation_task():
    """运行支付对账任务（由调度器调用）"""
    logger.info(
        "payment_reconciliation_task_started",
        message="开始执行支付对账任务"
    )

    await reconcile_pending_payments()


# 手动执行入口（用于测试）
if __name__ == "__main__":
    asyncio.run(run_payment_reconciliation_task())
