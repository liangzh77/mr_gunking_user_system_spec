"""计费服务 (BillingService) - T045

此服务负责游戏授权的计费和扣费逻辑。

核心职责:
1. 余额检查 - 确保账户余额充足
2. 会话ID幂等性检查 - 防止重复扣费
3. 扣费事务 - 使用行级锁确保并发安全
4. 使用记录创建 - 记录游戏会话详情
5. 交易记录创建 - 记录资金流动

关键特性:
- 数据库事务保证原子性
- SELECT FOR UPDATE行级锁防止并发冲突
- 会话ID唯一约束保证幂等性
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.application import Application
from ..models.operator import OperatorAccount
from ..models.site import OperationSite
from ..models.transaction import TransactionRecord
from ..models.usage_record import UsageRecord
from ..core.utils.db_lock import select_for_update


class BillingService:
    """计费服务

    负责游戏授权的扣费、记录创建等核心计费逻辑。
    """

    def __init__(self, db: AsyncSession):
        """初始化计费服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def check_session_idempotency(self, session_id: str) -> Optional[UsageRecord]:
        """检查会话ID幂等性

        如果会话ID已存在,返回已有的使用记录(防重复扣费)。

        Args:
            session_id: 游戏会话ID

        Returns:
            Optional[UsageRecord]: 已存在的使用记录,如果不存在则返回None
        """
        stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_balance_sufficiency(
        self,
        operator: OperatorAccount,
        required_amount: Decimal
    ) -> None:
        """检查账户余额是否充足

        Args:
            operator: 运营商账户对象
            required_amount: 所需金额

        Raises:
            HTTPException 402: 余额不足
        """
        if operator.balance < required_amount:
            shortage = required_amount - operator.balance
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error_code": "INSUFFICIENT_BALANCE",
                    "message": f"账户余额不足，当前余额: {operator.balance}元，需要: {required_amount}元",
                    "details": {
                        "current_balance": str(operator.balance),
                        "required_amount": str(required_amount),
                        "shortage": str(shortage)
                    }
                }
            )

    async def create_authorization_transaction(
        self,
        session_id: str,
        operator_id: UUID,
        site_id: UUID,
        application: Application,
        player_count: int,
        client_ip: Optional[str] = None
    ) -> tuple[UsageRecord, TransactionRecord, Decimal]:
        """创建授权扣费事务

        使用数据库事务和行级锁确保并发安全。

        事务流程:
        1. 锁定运营商账户行(SELECT FOR UPDATE)
        2. 计算总费用
        3. 验证余额充足
        4. 扣减余额
        5. 创建使用记录
        6. 创建交易记录

        Args:
            session_id: 游戏会话ID
            operator_id: 运营商ID
            site_id: 运营点ID
            application: 应用对象
            player_count: 玩家数量
            client_ip: 客户端IP(可选)

        Returns:
            tuple[UsageRecord, TransactionRecord, Decimal]: (使用记录, 交易记录, 扣费后余额)

        Raises:
            HTTPException 402: 余额不足
            HTTPException 409: 会话ID重复(幂等性冲突)
            HTTPException 500: 数据库并发冲突
        """
        # 计算费用
        total_cost = application.price_per_player * player_count

        try:
            # STEP 1: 使用SELECT FOR UPDATE锁定运营商账户行
            # 防止并发扣费导致余额计算错误
            operator = await select_for_update(
                self.db,
                OperatorAccount,
                operator_id
            )

            if not operator:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "OPERATOR_NOT_FOUND_IN_TRANSACTION",
                        "message": "事务中未找到运营商记录，请重试"
                    }
                )

            # STEP 2: 验证余额充足
            balance_before = operator.balance
            if balance_before < total_cost:
                shortage = total_cost - balance_before
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error_code": "INSUFFICIENT_BALANCE",
                        "message": f"账户余额不足，当前余额: {balance_before}元，需要: {total_cost}元",
                        "details": {
                            "current_balance": str(balance_before),
                            "required_amount": str(total_cost),
                            "shortage": str(shortage)
                        }
                    }
                )

            # STEP 3: 扣减余额
            operator.balance = balance_before - total_cost
            balance_after = operator.balance

            # STEP 4: 生成授权令牌
            authorization_token = str(uuid4())

            # STEP 5: 创建使用记录
            usage_record = UsageRecord(
                session_id=session_id,
                operator_id=operator_id,
                site_id=site_id,
                application_id=application.id,
                player_count=player_count,
                price_per_player=application.price_per_player,
                total_cost=total_cost,
                authorization_token=authorization_token,
                game_started_at=datetime.utcnow(),
                client_ip=client_ip
            )
            self.db.add(usage_record)

            # 需要flush来获取usage_record.id用于交易记录关联
            await self.db.flush()

            # STEP 6: 创建交易记录
            transaction_record = TransactionRecord(
                operator_id=operator_id,
                transaction_type="consumption",
                amount=-total_cost,  # 消费为负数
                balance_before=balance_before,
                balance_after=balance_after,
                related_usage_id=usage_record.id,
                description=f"游戏消费：{application.app_name} - {player_count}人"
            )
            self.db.add(transaction_record)

            # STEP 7: 提交事务
            await self.db.commit()

            return usage_record, transaction_record, balance_after

        except HTTPException:
            # HTTPException直接向上传播(包括402余额不足等业务异常)
            await self.db.rollback()
            raise

        except IntegrityError as e:
            # 捕获session_id唯一约束冲突(幂等性保护)
            await self.db.rollback()

            if "uq_session_id" in str(e).lower() or "session_id" in str(e).lower():
                # 会话ID重复,返回已有记录
                existing_record = await self.check_session_idempotency(session_id)
                if existing_record:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error_code": "SESSION_ID_DUPLICATE",
                            "message": "会话已存在，返回已授权信息(幂等性保护)",
                            "data": {
                                "session_id": existing_record.session_id,
                                "authorization_token": existing_record.authorization_token,
                                "total_cost": str(existing_record.total_cost),
                                "created_at": existing_record.created_at.isoformat()
                            }
                        }
                    )

            # 其他完整性错误
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "DATABASE_INTEGRITY_ERROR",
                    "message": "数据库完整性错误，请重试",
                    "details": str(e)
                }
            )

        except Exception as e:
            await self.db.rollback()
            # 记录日志并抛出通用错误
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "BILLING_TRANSACTION_FAILED",
                    "message": "扣费事务失败，请重试",
                    "details": str(e)
                }
            )

    async def get_usage_record_with_details(
        self,
        usage_record_id: UUID
    ) -> Optional[UsageRecord]:
        """获取使用记录及关联信息

        Args:
            usage_record_id: 使用记录ID

        Returns:
            Optional[UsageRecord]: 使用记录对象(包含关联的operator/site/application)
        """
        stmt = select(UsageRecord).where(UsageRecord.id == usage_record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def calculate_total_cost(
        self,
        price_per_player: Decimal,
        player_count: int
    ) -> Decimal:
        """计算总费用

        总费用 = 单人价格 × 玩家数量

        Args:
            price_per_player: 单人价格
            player_count: 玩家数量

        Returns:
            Decimal: 总费用(保留2位小数)
        """
        total = price_per_player * player_count
        # 确保精度为2位小数
        return total.quantize(Decimal('0.01'))
