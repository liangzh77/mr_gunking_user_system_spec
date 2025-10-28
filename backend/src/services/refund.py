"""退款服务 (RefundService) - T064

此服务提供退款管理的核心业务逻辑:
1. 退款申请创建 - 运营商提交退款申请
2. 可退余额计算 - 计算可退金额(当前余额)
3. 退款事务处理 - 财务审核通过后执行退款(扣减余额+记录交易)

业务规则:
- 只退当前余额,已消费金额不退
- 余额为0时无法申请退款
- 退款状态: pending(待审核) -> approved(已通过)/rejected(已拒绝)
- 审核通过后立即扣减余额并创建交易记录
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operator import OperatorAccount
from ..models.refund import RefundRecord
from ..models.transaction import TransactionRecord


class RefundService:
    """退款服务类

    提供退款申请、审核、事务处理功能
    """

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_refund_request(
        self,
        operator_id: UUID,
        reason: str
    ) -> RefundRecord:
        """创建退款申请 (T074辅助)

        业务规则:
        - 只退当前余额,已消费金额不退
        - 余额为0时无法申请
        - 退款状态初始为pending
        - requested_amount为申请时的余额快照

        Args:
            operator_id: 运营商ID
            reason: 退款原因

        Returns:
            RefundRecord: 新创建的退款申请记录

        Raises:
            HTTPException 400: 余额为0无法申请退款
            HTTPException 404: 运营商不存在
        """
        # 1. 验证运营商存在并获取余额
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await self.db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 2. 检查余额是否大于0
        if operator.balance <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_PARAMS",
                    "message": "当前余额为0，无法申请退款"
                }
            )

        # 3. 创建退款申请记录
        refund = RefundRecord(
            operator_id=operator_id,
            requested_amount=operator.balance,  # 申请时的余额快照
            status="pending",  # 初始状态为待审核
            refund_reason=reason
        )

        self.db.add(refund)
        await self.db.commit()
        await self.db.refresh(refund)

        return refund

    async def calculate_refundable_balance(
        self,
        operator_id: UUID
    ) -> Decimal:
        """计算可退余额

        可退余额 = 当前账户余额 (已消费金额不退)

        Args:
            operator_id: 运营商ID

        Returns:
            Decimal: 可退余额

        Raises:
            HTTPException 404: 运营商不存在
        """
        # 查询运营商账户
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await self.db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 返回当前余额作为可退余额
        return operator.balance

    async def approve_refund(
        self,
        refund_id: UUID,
        approved_by: UUID,
        actual_refund_amount: Optional[Decimal] = None
    ) -> RefundRecord:
        """审核通过退款申请

        业务流程:
        1. 查询退款申请并验证状态(必须是pending)
        2. 查询运营商账户并验证余额充足
        3. 数据库事务:
           - 更新退款记录状态为approved
           - 扣减运营商余额
           - 创建交易记录(refund类型)

        Args:
            refund_id: 退款申请ID
            approved_by: 审核人ID(财务人员)
            actual_refund_amount: 实际退款金额(可选,默认使用requested_amount)

        Returns:
            RefundRecord: 更新后的退款记录

        Raises:
            HTTPException 400: 退款申请状态不正确或余额不足
            HTTPException 404: 退款申请或运营商不存在
            HTTPException 500: 数据库事务失败
        """
        # 1. 查询退款申请
        refund_stmt = select(RefundRecord).where(
            RefundRecord.id == refund_id
        )
        refund_result = await self.db.execute(refund_stmt)
        refund = refund_result.scalar_one_or_none()

        if not refund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REFUND_NOT_FOUND",
                    "message": "退款申请不存在"
                }
            )

        # 2. 验证退款状态必须是pending
        if refund.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_REFUND_STATUS",
                    "message": f"退款申请状态不正确,当前状态: {refund.status}"
                }
            )

        # 3. 查询运营商账户
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == refund.operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await self.db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 4. 确定实际退款金额(默认使用申请金额)
        if actual_refund_amount is None:
            actual_refund_amount = refund.requested_amount

        # 5. 验证余额充足
        if operator.balance < actual_refund_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INSUFFICIENT_BALANCE",
                    "message": f"余额不足,当前余额: {operator.balance},退款金额: {actual_refund_amount}"
                }
            )

        # 6. 数据库事务:更新退款记录+扣减余额+创建交易记录
        try:
            # 更新退款记录
            refund.status = "approved"
            refund.actual_amount = actual_refund_amount
            refund.reviewed_by = approved_by
            refund.reviewed_at = datetime.now(timezone.utc)

            # 记录余额变化
            balance_before = operator.balance
            balance_after = balance_before - actual_refund_amount

            # 扣减运营商余额
            operator.balance = balance_after

            # 创建交易记录(refund类型,金额为负数)
            transaction = TransactionRecord(
                operator_id=operator.id,
                transaction_type="refund",
                amount=-actual_refund_amount,  # 负数表示扣减
                balance_before=balance_before,
                balance_after=balance_after,
                related_refund_id=refund.id,
                payment_status="success",
                description=f"退款: {actual_refund_amount}元"
            )

            self.db.add(transaction)
            await self.db.commit()
            await self.db.refresh(refund)

            return refund

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "TRANSACTION_FAILED",
                    "message": f"处理退款事务失败: {str(e)}"
                }
            )

    async def reject_refund(
        self,
        refund_id: UUID,
        reviewed_by: UUID,
        reject_reason: str
    ) -> RefundRecord:
        """拒绝退款申请

        Args:
            refund_id: 退款申请ID
            reviewed_by: 审核人ID(财务人员)
            reject_reason: 拒绝原因

        Returns:
            RefundRecord: 更新后的退款记录

        Raises:
            HTTPException 400: 退款申请状态不正确
            HTTPException 404: 退款申请不存在
        """
        # 1. 查询退款申请
        refund_stmt = select(RefundRecord).where(
            RefundRecord.id == refund_id
        )
        refund_result = await self.db.execute(refund_stmt)
        refund = refund_result.scalar_one_or_none()

        if not refund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REFUND_NOT_FOUND",
                    "message": "退款申请不存在"
                }
            )

        # 2. 验证退款状态必须是pending
        if refund.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_REFUND_STATUS",
                    "message": f"退款申请状态不正确,当前状态: {refund.status}"
                }
            )

        # 3. 更新退款记录状态为rejected
        refund.status = "rejected"
        refund.reject_reason = reject_reason
        refund.reviewed_by = reviewed_by
        refund.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(refund)

        return refund
