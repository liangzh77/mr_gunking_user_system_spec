#!/usr/bin/env python3
"""启用/禁用账户（从环境变量读取参数）"""
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount

async def toggle_active():
    # 从环境变量读取参数
    account_type = os.environ.get('ACCOUNT_TYPE')
    username = os.environ.get('ACCOUNT_USERNAME')
    is_active = os.environ.get('ACCOUNT_ACTIVE', 'true').lower() == 'true'

    # 根据类型选择模型
    if account_type == "admin":
        Model = AdminAccount
        type_name = "Admin"
    elif account_type == "operator":
        Model = OperatorAccount
        type_name = "Operator"
    elif account_type == "finance":
        Model = FinanceAccount
        type_name = "Finance"
    else:
        print(f"❌ Invalid account type: {account_type}")
        sys.exit(1)

    init_db()
    async with get_db_context() as session:
        # Query account
        result = await session.execute(
            select(Model).where(Model.username == username)
        )
        account = result.scalar_one_or_none()

        if not account:
            print(f"❌ {type_name} account not found!")
            sys.exit(1)

        # Toggle active status
        action_text = "enabled" if is_active else "disabled"
        account.is_active = is_active
        await session.commit()

        print(f"✅ {type_name} account {action_text} successfully!")
        print(f"  Username: {username}")
        print(f"  Status: {'✅ Active' if is_active else '❌ Disabled'}")

if __name__ == "__main__":
    asyncio.run(toggle_active())
