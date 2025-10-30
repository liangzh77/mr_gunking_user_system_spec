"""通知推送服务 (T214)

提供系统通知和消息推送功能：
- 系统公告推送（发送给所有运营商）
- 余额不足提醒
- 应用价格调整通知
- 授权到期提醒
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID as PyUUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operator import OperatorAccount
from ..models.authorization import OperatorAppAuthorization
from ..services.message_service import MessageService


class NotificationService:
    """通知推送服务

    负责向运营商发送各种系统通知。
    """

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.message_service = MessageService(db)

    async def send_system_announcement(
        self,
        title: str,
        content: str,
        importance: str = "normal",
        operator_ids: Optional[List[PyUUID]] = None
    ) -> dict:
        """发送系统公告给运营商

        Args:
            title: 公告标题
            content: 公告内容
            importance: 重要程度 (low/normal/high/urgent)
            operator_ids: 运营商ID列表（None=发送给所有运营商）

        Returns:
            dict: 发送结果 {success_count, failed_count, total_count}
        """
        # 如果未指定运营商，则获取所有活跃运营商
        if operator_ids is None:
            result = await self.db.execute(
                select(OperatorAccount.id).where(OperatorAccount.is_active == True)
            )
            operators = result.scalars().all()
            operator_ids = list(operators)

        # 批量创建消息
        success_count = 0
        failed_count = 0

        for operator_id in operator_ids:
            try:
                await self.message_service.create_message(
                    operator_id=operator_id,
                    message_type="system_announcement",
                    title=title,
                    content=content
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                # 记录错误但继续处理其他运营商
                print(f"发送公告失败 operator_id={operator_id}: {str(e)}")

        await self.db.commit()

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(operator_ids)
        }

    async def send_balance_low_alert(
        self,
        operator_id: PyUUID,
        current_balance: Decimal,
        threshold: Decimal = Decimal("100.00")
    ) -> None:
        """发送余额不足提醒

        Args:
            operator_id: 运营商ID
            current_balance: 当前余额
            threshold: 余额阈值
        """
        title = "余额不足提醒"
        content = f"您的账户余额已低于预警线。\n\n"
        content += f"当前余额: ¥{current_balance:.2f}\n"
        content += f"预警阈值: ¥{threshold:.2f}\n\n"
        content += f"为避免影响正常使用，请及时充值。"

        await self.message_service.create_message(
            operator_id=operator_id,
            message_type="balance_low",
            title=title,
            content=content
        )

        await self.db.commit()

    async def send_price_change_notification(
        self,
        application_id: PyUUID,
        app_name: str,
        old_price: Decimal,
        new_price: Decimal
    ) -> dict:
        """发送应用价格调整通知给所有授权该应用的运营商

        Args:
            application_id: 应用ID
            app_name: 应用名称
            old_price: 原价格
            new_price: 新价格

        Returns:
            dict: 发送结果
        """
        # 查询所有授权该应用的运营商
        result = await self.db.execute(
            select(OperatorAppAuthorization.operator_id)
            .where(
                OperatorAppAuthorization.application_id == application_id,
                OperatorAppAuthorization.is_active == True
            )
            .distinct()
        )
        operator_ids = result.scalars().all()

        if not operator_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "total_count": 0
            }

        # 构建通知内容
        title = f"应用价格调整通知 - {app_name}"
        content = f"您授权使用的应用'{app_name}'价格已调整。\n\n"
        content += f"原价格: ¥{old_price:.2f}/人\n"
        content += f"新价格: ¥{new_price:.2f}/人\n\n"

        if new_price > old_price:
            change_pct = ((new_price - old_price) / old_price * 100)
            content += f"价格上调: +¥{(new_price - old_price):.2f} (+{change_pct:.1f}%)\n"
        else:
            change_pct = ((old_price - new_price) / old_price * 100)
            content += f"价格下调: -¥{(old_price - new_price):.2f} (-{change_pct:.1f}%)\n"

        content += f"\n新价格将立即生效，感谢您的理解与支持。"

        # 批量发送通知
        success_count = 0
        failed_count = 0

        for operator_id in operator_ids:
            try:
                await self.message_service.create_message(
                    operator_id=operator_id,
                    message_type="price_change",
                    title=title,
                    content=content,
                    related_type="application",
                    related_id=application_id
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"发送价格变动通知失败 operator_id={operator_id}: {str(e)}")

        await self.db.commit()

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(operator_ids)
        }

    async def send_authorization_expiry_alert(
        self,
        operator_id: PyUUID,
        app_name: str,
        expires_at: datetime,
        days_remaining: int
    ) -> None:
        """发送授权到期提醒

        Args:
            operator_id: 运营商ID
            app_name: 应用名称
            expires_at: 到期时间
            days_remaining: 剩余天数
        """
        title = f"应用授权即将到期 - {app_name}"
        content = f"您授权使用的应用'{app_name}'即将到期。\n\n"
        content += f"到期时间: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"剩余天数: {days_remaining}天\n\n"
        content += f"到期后将无法继续使用该应用，请及时续期。"

        await self.message_service.create_message(
            operator_id=operator_id,
            message_type="authorization_expiry",
            title=title,
            content=content
        )

        await self.db.commit()

    async def send_custom_notification(
        self,
        operator_ids: List[PyUUID],
        message_type: str,
        title: str,
        content: str,
        related_type: Optional[str] = None,
        related_id: Optional[PyUUID] = None
    ) -> dict:
        """发送自定义通知

        Args:
            operator_ids: 运营商ID列表
            message_type: 消息类型
            title: 通知标题
            content: 通知内容
            related_type: 关联资源类型
            related_id: 关联资源ID

        Returns:
            dict: 发送结果
        """
        success_count = 0
        failed_count = 0

        for operator_id in operator_ids:
            try:
                await self.message_service.create_message(
                    operator_id=operator_id,
                    message_type=message_type,
                    title=title,
                    content=content,
                    related_type=related_type,
                    related_id=related_id
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"发送自定义通知失败 operator_id={operator_id}: {str(e)}")

        await self.db.commit()

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "total_count": len(operator_ids)
        }
