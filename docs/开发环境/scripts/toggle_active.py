#!/usr/bin/env python3
"""启用/禁用账户"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount

async def toggle_active(account_type, username, is_active):
    init_db()
    async with get_db_context() as session:
        # 根据类型选择模型
        if account_type == "admin":
            Model = AdminAccount
            type_name = "管理员"
        elif account_type == "operator":
            Model = OperatorAccount
            type_name = "运营商"
        elif account_type == "finance":
            Model = FinanceAccount
            type_name = "财务人员"
        else:
            print(f"❌ 无效的账户类型: {account_type}")
            sys.exit(1)

        # 查询账户
        result = await session.execute(
            select(Model).where(Model.username == username)
        )
        account = result.scalar_one_or_none()

        if not account:
            print(f"❌ {type_name}账户不存在！")
            sys.exit(1)

        # 修改状态
        action_text = "启用" if is_active else "禁用"
        account.is_active = is_active
        await session.commit()

        print(f"✅ {type_name}账户{action_text}成功！")
        print(f"  用户名: {username}")
        print(f"  当前状态: {'✅ 激活' if is_active else '❌ 禁用'}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python toggle_active.py <account_type> <username> <is_active>")
        print("account_type: admin, operator, finance")
        print("is_active: true, false")
        sys.exit(1)

    is_active = sys.argv[3].lower() == "true"
    asyncio.run(toggle_active(sys.argv[1], sys.argv[2], is_active))
