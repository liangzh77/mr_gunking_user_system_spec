"""运营商消息通知服务

此服务负责管理运营商的消息通知,包括:
- 退款审核结果通知
- 发票审核结果通知
- 系统公告
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.message import OperatorMessage
from ..core import NotFoundException, BadRequestException


class MessageService:
    """运营商消息通知服务类"""

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_message(
        self,
        operator_id: PyUUID,
        message_type: str,
        title: str,
        content: str,
        related_type: Optional[str] = None,
        related_id: Optional[PyUUID] = None
    ) -> OperatorMessage:
        """创建消息通知(通用方法)

        Args:
            operator_id: 运营商ID
            message_type: 消息类型
            title: 消息标题
            content: 消息内容
            related_type: 关联资源类型
            related_id: 关联资源ID

        Returns:
            OperatorMessage: 创建的消息对象
        """
        message = OperatorMessage(
            id=uuid4(),
            operator_id=operator_id,
            message_type=message_type,
            title=title,
            content=content,
            related_type=related_type,
            related_id=related_id,
            is_read=False,
            created_at=datetime.now(timezone.utc)
        )

        self.db.add(message)
        await self.db.flush()  # 刷新以获取ID,但不提交事务

        return message

    async def create_refund_approved_notification(
        self,
        operator_id: PyUUID,
        refund_id: PyUUID,
        refund_amount: str,
        actual_amount: str,
        note: Optional[str] = None
    ) -> OperatorMessage:
        """创建退款批准通知

        Args:
            operator_id: 运营商ID
            refund_id: 退款申请ID
            refund_amount: 申请退款金额
            actual_amount: 实际退款金额
            note: 财务备注

        Returns:
            OperatorMessage: 创建的消息对象
        """
        title = "退款申请已批准"
        content = f"您的退款申请已通过审核。\n\n"
        content += f"申请金额: ¥{refund_amount}\n"
        content += f"实际退款: ¥{actual_amount}\n"

        if note:
            content += f"\n财务备注: {note}"

        return await self.create_message(
            operator_id=operator_id,
            message_type="refund_approved",
            title=title,
            content=content,
            related_type="refund",
            related_id=refund_id
        )

    async def create_refund_rejected_notification(
        self,
        operator_id: PyUUID,
        refund_id: PyUUID,
        refund_amount: str,
        reject_reason: str
    ) -> OperatorMessage:
        """创建退款拒绝通知

        Args:
            operator_id: 运营商ID
            refund_id: 退款申请ID
            refund_amount: 申请退款金额
            reject_reason: 拒绝原因

        Returns:
            OperatorMessage: 创建的消息对象
        """
        title = "退款申请被拒绝"
        content = f"很抱歉,您的退款申请未通过审核。\n\n"
        content += f"申请金额: ¥{refund_amount}\n"
        content += f"拒绝原因: {reject_reason}\n\n"
        content += f"如有疑问,请联系客服。"

        return await self.create_message(
            operator_id=operator_id,
            message_type="refund_rejected",
            title=title,
            content=content,
            related_type="refund",
            related_id=refund_id
        )

    async def create_invoice_approved_notification(
        self,
        operator_id: PyUUID,
        invoice_id: PyUUID,
        invoice_amount: str,
        invoice_number: str,
        pdf_url: str,
        note: Optional[str] = None
    ) -> OperatorMessage:
        """创建发票批准通知

        Args:
            operator_id: 运营商ID
            invoice_id: 发票申请ID
            invoice_amount: 发票金额
            invoice_number: 发票号码
            pdf_url: 发票PDF下载链接
            note: 财务备注

        Returns:
            OperatorMessage: 创建的消息对象
        """
        title = "发票已开具"
        content = f"您的发票申请已通过审核,发票已成功开具。\n\n"
        content += f"发票金额: ¥{invoice_amount}\n"
        content += f"发票号码: {invoice_number}\n"
        content += f"下载链接: {pdf_url}\n"

        if note:
            content += f"\n财务备注: {note}"

        return await self.create_message(
            operator_id=operator_id,
            message_type="invoice_approved",
            title=title,
            content=content,
            related_type="invoice",
            related_id=invoice_id
        )

    async def create_invoice_rejected_notification(
        self,
        operator_id: PyUUID,
        invoice_id: PyUUID,
        invoice_amount: str,
        reject_reason: str
    ) -> OperatorMessage:
        """创建发票拒绝通知

        Args:
            operator_id: 运营商ID
            invoice_id: 发票申请ID
            invoice_amount: 发票金额
            reject_reason: 拒绝原因

        Returns:
            OperatorMessage: 创建的消息对象
        """
        title = "发票申请被拒绝"
        content = f"很抱歉,您的发票申请未通过审核。\n\n"
        content += f"发票金额: ¥{invoice_amount}\n"
        content += f"拒绝原因: {reject_reason}\n\n"
        content += f"请根据拒绝原因重新提交申请。"

        return await self.create_message(
            operator_id=operator_id,
            message_type="invoice_rejected",
            title=title,
            content=content,
            related_type="invoice",
            related_id=invoice_id
        )

    async def get_messages(
        self,
        operator_id: PyUUID,
        is_read: Optional[bool] = None,
        message_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[OperatorMessage], int]:
        """获取运营商消息列表(分页)

        Args:
            operator_id: 运营商ID
            is_read: 是否已读筛选(None=全部)
            message_type: 消息类型筛选(None=全部)
            page: 页码(从1开始)
            page_size: 每页数量

        Returns:
            tuple: (消息列表, 总数)
        """
        # 构建查询条件
        conditions = [OperatorMessage.operator_id == operator_id]

        if is_read is not None:
            conditions.append(OperatorMessage.is_read == is_read)

        if message_type:
            conditions.append(OperatorMessage.message_type == message_type)

        # 查询总数
        count_query = select(func.count()).select_from(OperatorMessage).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # 查询消息列表(按创建时间倒序)
        query = (
            select(OperatorMessage)
            .where(and_(*conditions))
            .order_by(desc(OperatorMessage.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        messages = result.scalars().all()

        return list(messages), total

    async def mark_as_read(
        self,
        message_id: PyUUID,
        operator_id: PyUUID
    ) -> OperatorMessage:
        """标记消息为已读

        Args:
            message_id: 消息ID
            operator_id: 运营商ID(用于验证权限)

        Returns:
            OperatorMessage: 更新后的消息对象

        Raises:
            NotFoundException: 消息不存在或无权限
            BadRequestException: 消息已读
        """
        # 查询消息
        result = await self.db.execute(
            select(OperatorMessage).where(
                and_(
                    OperatorMessage.id == message_id,
                    OperatorMessage.operator_id == operator_id
                )
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            raise NotFoundException("消息不存在或无权限访问")

        if message.is_read:
            raise BadRequestException("消息已读")

        # 标记为已读
        message.is_read = True
        message.read_at = datetime.now(timezone.utc)

        await self.db.flush()

        return message

    async def mark_all_as_read(
        self,
        operator_id: PyUUID
    ) -> int:
        """标记所有未读消息为已读

        Args:
            operator_id: 运营商ID

        Returns:
            int: 标记的消息数量
        """
        # 查询所有未读消息
        result = await self.db.execute(
            select(OperatorMessage).where(
                and_(
                    OperatorMessage.operator_id == operator_id,
                    OperatorMessage.is_read == False
                )
            )
        )
        messages = result.scalars().all()

        # 标记为已读
        now = datetime.now(timezone.utc)
        for message in messages:
            message.is_read = True
            message.read_at = now

        await self.db.flush()

        return len(messages)

    async def get_unread_count(
        self,
        operator_id: PyUUID
    ) -> int:
        """获取未读消息数量

        Args:
            operator_id: 运营商ID

        Returns:
            int: 未读消息数量
        """
        result = await self.db.execute(
            select(func.count()).select_from(OperatorMessage).where(
                and_(
                    OperatorMessage.operator_id == operator_id,
                    OperatorMessage.is_read == False
                )
            )
        )
        return result.scalar()

    async def delete_message(
        self,
        message_id: PyUUID,
        operator_id: PyUUID
    ) -> None:
        """删除消息

        Args:
            message_id: 消息ID
            operator_id: 运营商ID(用于验证权限)

        Raises:
            NotFoundException: 消息不存在或无权限
        """
        # 查询消息
        result = await self.db.execute(
            select(OperatorMessage).where(
                and_(
                    OperatorMessage.id == message_id,
                    OperatorMessage.operator_id == operator_id
                )
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            raise NotFoundException("消息不存在或无权限访问")

        # 删除消息
        await self.db.delete(message)
        await self.db.flush()
