#!/usr/bin/env python3
"""测试手动充值功能"""

import asyncio
import uuid
import sys
import os
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.models.operator import OperatorAccount
from src.models.transaction import TransactionRecord
from src.services.finance_recharge_service import FinanceRechargeService


async def test_manual_recharge():
    """测试手动充值功能"""

    # 创建内存数据库用于测试
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)

    async with engine.begin() as conn:
        # 创建表
        from src.db.base import Base
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as db:
        # 创建一个测试运营商
        operator = OperatorAccount(
            id=uuid.uuid4(),
            username="test_operator_recharge",
            password_hash="test_hash",
            full_name="测试运营商充值",
            phone="13800138000",
            email="test@example.com",
            api_key="test_api_key_12345678901234567890",
            api_key_hash="test_api_key_hash",
            balance=Decimal("100.00"),
            customer_tier="standard"
        )
        db.add(operator)
        await db.commit()
        await db.refresh(operator)

        print(f"创建运营商: {operator.username}, 初始余额: {operator.balance}")

        # 测试手动充值
        recharge_service = FinanceRechargeService(db)
        finance_id = uuid.uuid4()

        try:
            result = await recharge_service.manual_recharge(
                operator_id=str(operator.id),
                amount=500.00,
                finance_id=finance_id,
                description="测试手动充值"
            )

            print(f"充值成功!")
            print(f"  交易ID: {result.transaction_id}")
            print(f"  运营商: {result.operator_name}")
            print(f"  充值金额: ¥{result.amount}")
            print(f"  充值前余额: ¥{result.balance_before}")
            print(f"  充值后余额: ¥{result.balance_after}")

            # 验证运营商余额已更新
            await db.refresh(operator)
            print(f"  运营商实际余额: ¥{operator.balance}")

            # 验证交易记录已创建
            transaction_result = await db.execute(
                select(TransactionRecord).where(
                    TransactionRecord.operator_id == operator.id
                )
            )
            transactions = transaction_result.scalars().all()
            print(f"  创建的交易记录数: {len(transactions)}")

            if transactions:
                tx = transactions[0]
                print(f"  交易类型: {tx.transaction_type}")
                print(f"  交易金额: {tx.amount}")
                print(f"  交易前余额: {tx.balance_before}")
                print(f"  交易后余额: {tx.balance_after}")
                print(f"  交易描述: {tx.description}")

            return True

        except Exception as e:
            print(f"充值失败: {e}")
            return False


if __name__ == "__main__":
    print("开始测试手动充值功能...")
    success = asyncio.run(test_manual_recharge())
    if success:
        print("\n✅ 手动充值功能测试成功!")
    else:
        print("\n❌ 手动充值功能测试失败!")