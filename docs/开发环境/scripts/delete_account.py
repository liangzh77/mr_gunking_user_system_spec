#!/usr/bin/env python3
"""删除账户"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount

async def delete_account(account_type, username):
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

        # 显示账户信息
        print(f"\n将要删除的{type_name}账户信息:")
        print(f"  用户名: {account.username}")
        print(f"  姓名: {account.full_name}")
        print(f"  邮箱: {account.email}")
        if hasattr(account, 'role'):
            print(f"  角色: {account.role}")
        if hasattr(account, 'balance'):
            print(f"  余额: ¥{float(account.balance):.2f}")
        print(f"  状态: {'激活' if account.is_active else '禁用'}")

        # 删除账户
        await session.delete(account)
        await session.commit()

        print(f"\n✅ {type_name}账户删除成功！")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python delete_account.py <account_type> <username>")
        print("account_type: admin, operator, finance")
        sys.exit(1)

    asyncio.run(delete_account(sys.argv[1], sys.argv[2]))
