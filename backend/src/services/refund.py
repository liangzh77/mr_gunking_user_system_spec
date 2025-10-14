"""退款服务 (RefundService) - T064

实现退款申请业务逻辑:
- 创建退款申请
- 可退余额计算
- 退款事务处理(财务审核时调用)

业务规则:
- 仅退还当前账户余额(已消费金额不退)
- 余额为0时无法申请退款
- 退款需财务人员审核
- 审核通过后余额清零
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_logger
from ..models.operator import OperatorAccount
from ..models.refund import RefundRecord

logger = get_logger(__name__)


class RefundService:
    """退款服务类"""

    def __init__(self, db: AsyncSession):
        """初始化RefundService

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_refund_request(
        self,
        operator_id: UUID,
        reason: str
    ) -> RefundRecord:
        """创建退款申请

        Args:
            operator_id: 运营商ID
            reason: 退款原因(10-500字符)

        Returns:
            RefundRecord: 退款申请记录

        Raises:
            ValueError: 余额为0时无法申请退款
        """
        # 1. 查询运营商当前余额
        stmt = select(OperatorAccount).where(OperatorAccount.id == operator_id)
        result = await self.db.execute(stmt)
        operator = result.scalar_one()

        current_balance = operator.balance

        # 2. 验证余额 > 0
        if current_balance <= 0:
            logger.warning(
                "refund_request_zero_balance",
                operator_id=str(operator_id),
                balance=str(current_balance)
            )
            raise ValueError("当前余额为0,无法申请退款")

        # 3. 创建退款申请记录
        refund_record = RefundRecord(
            id=uuid4(),
            operator_id=operator_id,
            requested_amount=current_balance,
            reason=reason,
            status="pending"  # 待审核
        )

        self.db.add(refund_record)
        await self.db.commit()
        await self.db.refresh(refund_record)

        logger.info(
            "refund_request_created",
            refund_id=str(refund_record.id),
            operator_id=str(operator_id),
            requested_amount=str(current_balance),
            reason_length=len(reason)
        )

        return refund_record

    async def get_refundable_balance(self, operator_id: UUID) -> Decimal:
        """计算可退款余额(当前账户余额)

        Args:
            operator_id: 运营商ID

        Returns:
            Decimal: 可退款金额
        """
        stmt = select(OperatorAccount.balance).where(
            OperatorAccount.id == operator_id
        )
        result = await self.db.execute(stmt)
        balance = result.scalar_one()

        return balance

    async def process_refund_approval(
        self,
        refund_id: UUID,
        reviewer_id: UUID,
        actual_amount: Optional[Decimal] = None
    ) -> RefundRecord:
        """处理退款审核通过(财务人员调用)

        Args:
            refund_id: 退款申请ID
            reviewer_id: 审核人ID(财务人员)
            actual_amount: 实际退款金额(可选,默认使用当前余额)

        Returns:
            RefundRecord: 更新后的退款记录

        Note:
            此方法用于US6财务后台,当前阶段不实现完整逻辑
        """
        # TODO: US6实现时完善此方法
        # 1. 查询退款申请
        # 2. 查询运营商当前余额
        # 3. 更新退款记录状态为approved
        # 4. 扣减运营商余额
        # 5. 创建交易记录
        # 6. 记录审核信息
        raise NotImplementedError("此方法将在User Story 6实现")

    async def process_refund_rejection(
        self,
        refund_id: UUID,
        reviewer_id: UUID,
        reject_reason: str
    ) -> RefundRecord:
        """处理退款审核拒绝(财务人员调用)

        Args:
            refund_id: 退款申请ID
            reviewer_id: 审核人ID(财务人员)
            reject_reason: 拒绝原因

        Returns:
            RefundRecord: 更新后的退款记录

        Note:
            此方法用于US6财务后台,当前阶段不实现完整逻辑
        """
        # TODO: US6实现时完善此方法
        raise NotImplementedError("此方法将在User Story 6实现")
