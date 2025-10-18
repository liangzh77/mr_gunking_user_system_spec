#!/usr/bin/env python
"""修复数据库中的 customer_tier 值"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from src.core.config import get_settings
from src.models.operator import OperatorAccount


async def fix_customer_tier():
    """将 customer_tier 从 'standard' 改为 'normal'"""
    print("="*60)
    print("修复 customer_tier 字段")
    print("="*60)
    print()

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 查询所有 customer_tier = 'standard' 的账户
            result = await session.execute(
                select(OperatorAccount).where(OperatorAccount.customer_tier == "standard")
            )
            operators = result.scalars().all()

            print(f"找到 {len(operators)} 个账户需要更新")
            print()

            if len(operators) > 0:
                # 更新所有账户
                stmt = (
                    update(OperatorAccount)
                    .where(OperatorAccount.customer_tier == "standard")
                    .values(customer_tier="normal")
                )
                await session.execute(stmt)
                await session.commit()

                print(f"✅ 成功更新 {len(operators)} 个账户的 customer_tier 从 'standard' 到 'normal'")
            else:
                print("✅ 没有需要更新的账户")

    finally:
        await engine.dispose()

    print()
    print("="*60)
    print("修复完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(fix_customer_tier())
