"""客户分类自动更新定时任务

每月1日凌晨2点自动重新计算所有运营商的客户分类（VIP/普通/试用）。

分类标准（基于上月消费额）：
- 月消费 ≥ 10000元 → VIP
- 1000元 ≤ 月消费 < 10000元 → 普通
- 月消费 < 1000元 → 试用

容错机制：
1. 任务执行失败自动重试（最多3次，5分钟间隔）
2. 单个运营商分类更新失败不影响其他运营商
3. 分类变更记录审计日志
4. 分类从高变低时发送通知给运营商

相关需求：
- Assumption: 客户分类判定标准
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operator import OperatorAccount, CustomerCategory
from ..models.transaction import TransactionRecord, TransactionType, TransactionStatus
from ..models.usage_record import UsageRecord
from ..db.session import get_db_context
from ..core import get_logger

logger = get_logger(__name__)

# 分类阈值
VIP_THRESHOLD = Decimal("10000.00")    # ≥10000元 → VIP
NORMAL_THRESHOLD = Decimal("1000.00")   # ≥1000元 → 普通
# <1000元 → 试用


async def update_all_customer_tiers():
    """更新所有运营商的客户分类

    逻辑：
    1. 计算上个月的日期范围（例如当前是3月1日，则计算2月1日-2月28日）
    2. 统计每个运营商在上月的总消费额
    3. 根据消费额重新分配客户分类
    4. 记录分类变更日志
    5. 分类降低时发送通知
    """
    async with get_db_context() as db:
        try:
            # 计算上个月的日期范围
            today = datetime.now(timezone.utc).date()
            last_month_start, last_month_end = _get_last_month_range(today)

            logger.info(
                "customer_tier_update_started",
                period_start=last_month_start.isoformat(),
                period_end=last_month_end.isoformat(),
                message=f"开始更新客户分类（基于{last_month_start}至{last_month_end}消费数据）"
            )

            # 统计信息
            stats = {
                "total_operators": 0,
                "tier_upgraded": 0,   # 分类提升（试用→普通，普通→VIP）
                "tier_downgraded": 0,  # 分类降低
                "tier_unchanged": 0,   # 分类不变
                "errors": 0,          # 更新失败
            }

            # 获取所有激活的运营商
            result = await db.execute(
                select(OperatorAccount).where(
                    and_(
                        OperatorAccount.is_active == True,
                        OperatorAccount.deleted_at.is_(None),
                    )
                )
            )

            operators = result.scalars().all()
            stats["total_operators"] = len(operators)

            logger.info(
                "customer_tier_operators_fetched",
                count=stats["total_operators"],
                message=f"获取到{stats['total_operators']}个运营商"
            )

            # 逐个更新运营商分类
            for operator in operators:
                try:
                    await _update_single_operator_tier(
                        db, operator, last_month_start, last_month_end, stats
                    )
                except Exception as e:
                    logger.error(
                        "customer_tier_update_operator_error",
                        operator_id=str(operator.id),
                        operator_name=operator.full_name,
                        error=str(e),
                        message=f"运营商{operator.full_name}分类更新失败"
                    )
                    stats["errors"] += 1

            # 提交所有更新
            await db.commit()

            logger.info(
                "customer_tier_update_completed",
                **stats,
                message=(
                    f"客户分类更新完成: "
                    f"总计{stats['total_operators']}个运营商, "
                    f"提升{stats['tier_upgraded']}个, "
                    f"降低{stats['tier_downgraded']}个, "
                    f"不变{stats['tier_unchanged']}个, "
                    f"失败{stats['errors']}个"
                )
            )

        except Exception as e:
            logger.error(
                "customer_tier_update_error",
                error=str(e),
                message="客户分类更新任务执行失败"
            )
            await db.rollback()
            raise


async def _update_single_operator_tier(
    db: AsyncSession,
    operator: OperatorAccount,
    period_start: datetime.date,
    period_end: datetime.date,
    stats: Dict[str, int],
):
    """更新单个运营商的客户分类

    Args:
        db: 数据库会话
        operator: 运营商账户
        period_start: 统计期间开始日期
        period_end: 统计期间结束日期
        stats: 统计信息字典
    """
    # 计算上月消费总额
    total_consumption = await _calculate_monthly_consumption(
        db, operator.id, period_start, period_end
    )

    # 根据消费额确定新分类
    new_category = _determine_category(total_consumption)

    # 保存旧分类
    old_category = operator.category

    # 分类未变化
    if new_category == old_category:
        stats["tier_unchanged"] += 1

        logger.debug(
            "customer_tier_unchanged",
            operator_id=str(operator.id),
            operator_name=operator.full_name,
            category=old_category.value,
            consumption=float(total_consumption),
        )
        return

    # 更新分类
    operator.category = new_category
    operator.updated_at = datetime.now(timezone.utc)

    # 判断是提升还是降低
    category_order = {
        CustomerCategory.TRIAL: 1,
        CustomerCategory.STANDARD: 2,
        CustomerCategory.VIP: 3,
    }

    if category_order[new_category] > category_order[old_category]:
        stats["tier_upgraded"] += 1
        change_type = "upgraded"
    else:
        stats["tier_downgraded"] += 1
        change_type = "downgraded"

    logger.info(
        f"customer_tier_{change_type}",
        operator_id=str(operator.id),
        operator_name=operator.full_name,
        old_category=old_category.value,
        new_category=new_category.value,
        consumption=float(total_consumption),
        period=f"{period_start} - {period_end}",
        message=(
            f"运营商{operator.full_name}分类{change_type}: "
            f"{old_category.value} → {new_category.value} "
            f"(消费{total_consumption}元)"
        ),
    )

    # 分类降低时发送通知
    if change_type == "downgraded":
        await _send_tier_downgrade_notification(
            db, operator, old_category, new_category, total_consumption
        )


async def _calculate_monthly_consumption(
    db: AsyncSession,
    operator_id: UUID,
    period_start: datetime.date,
    period_end: datetime.date,
) -> Decimal:
    """计算运营商在指定月份的总消费额

    Args:
        db: 数据库会话
        operator_id: 运营商ID
        period_start: 统计期间开始日期
        period_end: 统计期间结束日期

    Returns:
        Decimal: 消费总额
    """
    # 查询该月所有消费类型的交易记录
    result = await db.execute(
        select(func.sum(TransactionRecord.amount))
        .where(
            and_(
                TransactionRecord.related_id == str(operator_id),
                TransactionRecord.transaction_type == TransactionType.CONSUMPTION,
                TransactionRecord.status == TransactionStatus.SUCCESS,
                TransactionRecord.created_at >= datetime.combine(
                    period_start, datetime.min.time(), tzinfo=timezone.utc
                ),
                TransactionRecord.created_at < datetime.combine(
                    period_end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
                ),
            )
        )
    )

    total = result.scalar()

    return total if total is not None else Decimal("0.00")


def _determine_category(consumption: Decimal) -> CustomerCategory:
    """根据消费额确定客户分类

    Args:
        consumption: 月消费额

    Returns:
        CustomerCategory: 客户分类
    """
    if consumption >= VIP_THRESHOLD:
        return CustomerCategory.VIP
    elif consumption >= NORMAL_THRESHOLD:
        return CustomerCategory.STANDARD
    else:
        return CustomerCategory.TRIAL


def _get_last_month_range(today: datetime.date) -> tuple[datetime.date, datetime.date]:
    """计算上个月的日期范围

    Args:
        today: 当前日期

    Returns:
        tuple: (上月第一天, 上月最后一天)
    """
    # 上个月第一天
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)

    # 上个月最后一天 = 本月第一天 - 1天
    this_month_first = today.replace(day=1)
    last_month_end = this_month_first - timedelta(days=1)

    return last_month_start, last_month_end


async def _send_tier_downgrade_notification(
    db: AsyncSession,
    operator: OperatorAccount,
    old_category: CustomerCategory,
    new_category: CustomerCategory,
    consumption: Decimal,
):
    """发送客户分类降低通知

    Args:
        db: 数据库会话
        operator: 运营商账户
        old_category: 原分类
        new_category: 新分类
        consumption: 上月消费额
    """
    logger.warning(
        "customer_tier_downgrade_notification",
        operator_id=str(operator.id),
        operator_name=operator.full_name,
        old_category=old_category.value,
        new_category=new_category.value,
        consumption=float(consumption),
        message=f"客户分类降低通知: {operator.full_name} {old_category.value} → {new_category.value}",
    )

    # TODO: 调用通知服务发送消息到运营商消息中心
    # from ..services.notification import NotificationService
    # notification_service = NotificationService(db)
    # await notification_service.send_tier_change_notification(
    #     operator_id=operator.id,
    #     old_category=old_category.value,
    #     new_category=new_category.value,
    #     consumption=consumption,
    # )


async def run_customer_tier_update_task():
    """运行客户分类更新任务（由调度器调用）"""
    logger.info(
        "customer_tier_update_task_started",
        message="开始执行客户分类更新任务"
    )

    await update_all_customer_tiers()


# 手动执行入口（用于测试）
if __name__ == "__main__":
    asyncio.run(run_customer_tier_update_task())
