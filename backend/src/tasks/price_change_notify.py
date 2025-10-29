"""价格调整自动通知任务 (T221)

当应用价格调整时，自动通知所有授权该应用的运营商

使用方式：
- 在更新应用价格后，调用 notify_price_change() 函数
- 也可以作为定时任务检查价格变更记录
"""

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.application import Application
from ..services.notification import NotificationService
from ..core import get_logger

logger = get_logger(__name__)


async def notify_price_change(
    db: AsyncSession,
    application_id: str,
    old_price: Decimal,
    new_price: Decimal
):
    """通知应用价格调整

    当应用价格发生变化时调用此函数，会自动通知所有授权该应用的运营商。

    Args:
        db: 数据库会话
        application_id: 应用ID
        old_price: 原价格
        new_price: 新价格

    用法示例：
        在 AdminService.update_application_price() 中调用：
        ```python
        # 更新价格后
        if price_per_player != app.price_per_player:
            await notify_price_change(
                db=self.db,
                application_id=app.id,
                old_price=app.price_per_player,
                new_price=price_per_player
            )
        ```
    """
    try:
        # 获取应用信息
        from sqlalchemy import select
        from uuid import UUID

        app_uuid = UUID(application_id) if isinstance(application_id, str) else application_id

        result = await db.execute(
            select(Application).where(Application.id == app_uuid)
        )
        app = result.scalar_one_or_none()

        if not app:
            logger.warning(
                "price_change_notify_app_not_found",
                application_id=str(application_id),
                message="应用不存在"
            )
            return

        # 发送价格变更通知
        notification_service = NotificationService(db)
        result = await notification_service.send_price_change_notification(
            application_id=app.id,
            app_name=app.app_name,
            old_price=old_price,
            new_price=new_price
        )

        logger.info(
            "price_change_notify_sent",
            application_id=str(app.id),
            app_name=app.app_name,
            old_price=float(old_price),
            new_price=float(new_price),
            success_count=result["success_count"],
            failed_count=result["failed_count"],
            total_count=result["total_count"],
            message=f"价格调整通知已发送：{app.app_name} ¥{old_price}→¥{new_price}"
        )

        return result

    except Exception as e:
        logger.error(
            "price_change_notify_error",
            application_id=str(application_id),
            error=str(e),
            message="价格调整通知发送失败"
        )
        raise


async def batch_notify_price_changes(
    db: AsyncSession,
    price_changes: list[dict]
):
    """批量通知多个应用的价格调整

    Args:
        db: 数据库会话
        price_changes: 价格变更列表，每个元素包含:
            - application_id: 应用ID
            - old_price: 原价格
            - new_price: 新价格

    用法示例：
        ```python
        price_changes = [
            {
                "application_id": "uuid1",
                "old_price": Decimal("50.00"),
                "new_price": Decimal("60.00")
            },
            {
                "application_id": "uuid2",
                "old_price": Decimal("70.00"),
                "new_price": Decimal("65.00")
            }
        ]
        await batch_notify_price_changes(db, price_changes)
        ```
    """
    results = []

    for change in price_changes:
        try:
            result = await notify_price_change(
                db=db,
                application_id=change["application_id"],
                old_price=change["old_price"],
                new_price=change["new_price"]
            )
            results.append({
                "application_id": change["application_id"],
                "success": True,
                "result": result
            })
        except Exception as e:
            results.append({
                "application_id": change["application_id"],
                "success": False,
                "error": str(e)
            })

    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count

    logger.info(
        "batch_price_change_notify_completed",
        total=len(results),
        success=success_count,
        failed=failed_count,
        message=f"批量价格调整通知完成: {success_count}/{len(results)}"
    )

    return results


# ========== 集成到AdminService的辅助函数 ==========

def get_price_change_notifier():
    """获取价格变更通知函数

    返回一个可以被AdminService调用的函数。

    用法示例（在 AdminService.update_application() 中）：
        ```python
        from ..tasks.price_change_notify import get_price_change_notifier

        async def update_application(self, app_id, ...):
            # ... 更新逻辑 ...

            # 如果价格变化，发送通知
            if price_per_player and price_per_player != app.price_per_player:
                old_price = app.price_per_player
                app.price_per_player = Decimal(str(price_per_player))

                # 发送通知
                notify_fn = get_price_change_notifier()
                await notify_fn(
                    db=self.db,
                    application_id=str(app.id),
                    old_price=old_price,
                    new_price=app.price_per_player
                )
        ```
    """
    return notify_price_change
