"""财务充值服务 (T179)

此服务处理财务人员为运营商手动充值的业务逻辑。
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID as PyUUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import BadRequestException, NotFoundException
from ..models.operator import OperatorAccount
from ..models.transaction import TransactionRecord
from ..models.finance import FinanceOperationLog
from ..schemas.finance import RechargeResponse


class FinanceRechargeService:
    """财务充值服务"""

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 异步数据库会话
        """
        self.db = db

    async def manual_recharge(
        self,
        operator_id: str,
        amount: float,
        finance_id: PyUUID,
        description: Optional[str] = None,
        payment_proof_path: Optional[str] = None
    ) -> RechargeResponse:
        """为运营商手动充值

        Args:
            operator_id: 运营商ID
            amount: 充值金额
            finance_id: 财务人员ID
            description: 充值备注
            payment_proof_path: 付款凭证文件路径

        Returns:
            RechargeResponse: 充值结果

        Raises:
            BadRequestException: 请求参数错误
            NotFoundException: 运营商不存在
        """
        # 验证运营商ID格式
        try:
            operator_uuid = PyUUID(operator_id)
        except ValueError:
            raise BadRequestException(f"无效的运营商ID格式: {operator_id}")

        # 查询运营商
        result = await self.db.execute(
            select(OperatorAccount).where(
                OperatorAccount.id == operator_uuid,
                OperatorAccount.deleted_at.is_(None)
            )
        )
        operator = result.scalar_one_or_none()

        if not operator:
            raise NotFoundException(f"运营商 {operator_id} 不存在")

        # 验证运营商状态
        if not operator.is_active:
            raise BadRequestException(f"运营商 {operator.username} 账户已注销")

        if operator.is_locked:
            raise BadRequestException(f"运营商 {operator.username} 账户已被锁定")

        # 验证充值金额
        if amount <= 0:
            raise BadRequestException("充值金额必须大于0")

        # 转换为Decimal类型
        amount_decimal = Decimal(str(amount))

        # 开始事务处理
        try:
            # 记录充值前余额
            balance_before = operator.balance

            # 更新运营商余额
            operator.balance += amount_decimal

            # 记录充值后余额
            balance_after = operator.balance

            # 创建交易记录
            transaction = TransactionRecord(
                id=uuid4(),
                operator_id=operator.id,
                transaction_type="recharge",
                amount=amount_decimal,
                balance_before=balance_before,
                balance_after=balance_after,
                description=description or f"财务手动充值 ¥{amount_decimal}",
                payment_channel="manual",
                payment_status="success",
                payment_callback_at=datetime.now()
            )
            self.db.add(transaction)

            # 创建财务操作审计日志
            operation_log = FinanceOperationLog(
                id=uuid4(),
                finance_account_id=finance_id,
                operation_type="manual_recharge",
                target_resource_type="operator",
                target_resource_id=operator.id,
                operation_details={
                    "operator_id": str(operator.id),
                    "operator_name": operator.username,
                    "amount": float(amount_decimal),
                    "balance_before": float(balance_before),
                    "balance_after": float(balance_after),
                    "description": description,
                    "payment_proof_path": payment_proof_path
                },
                ip_address="127.0.0.1",  # TODO: 从请求中获取实际IP
                user_agent="finance-api"  # TODO: 从请求中获取实际User-Agent
            )
            self.db.add(operation_log)

            # 提交事务
            await self.db.commit()

            # 构建响应
            return RechargeResponse(
                transaction_id=str(transaction.id),
                operator_id=str(operator.id),
                operator_name=operator.username,
                amount=f"{amount_decimal:.2f}",
                balance_before=f"{balance_before:.2f}",
                balance_after=f"{balance_after:.2f}",
                description=description,
                created_at=transaction.created_at
            )

        except Exception as e:
            await self.db.rollback()
            raise BadRequestException(f"充值失败: {str(e)}")

    async def get_operator_balance(self, operator_id: str) -> Decimal:
        """获取运营商当前余额

        Args:
            operator_id: 运营商ID

        Returns:
            Decimal: 运营商余额

        Raises:
            BadRequestException: 运营商ID格式错误
            NotFoundException: 运营商不存在
        """
        try:
            operator_uuid = PyUUID(operator_id)
        except ValueError:
            raise BadRequestException(f"无效的运营商ID格式: {operator_id}")

        result = await self.db.execute(
            select(OperatorAccount.balance).where(
                OperatorAccount.id == operator_uuid,
                OperatorAccount.deleted_at.is_(None)
            )
        )
        balance = result.scalar_one_or_none()

        if balance is None:
            raise NotFoundException(f"运营商 {operator_id} 不存在")

        return balance

    async def get_operators_list(self) -> list[dict]:
        """获取运营商列表（用于充值选择）

        Returns:
            list[dict]: 运营商列表
        """
        result = await self.db.execute(
            select(OperatorAccount).where(
                OperatorAccount.deleted_at.is_(None),
                OperatorAccount.is_active.is_(True)
            ).order_by(OperatorAccount.username)
        )
        operators = result.scalars().all()

        return [
            {
                "id": str(operator.id),
                "username": operator.username,
                "full_name": operator.full_name,
                "balance": float(operator.balance),
                "customer_tier": operator.customer_tier
            }
            for operator in operators
        ]