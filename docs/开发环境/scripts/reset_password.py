#!/usr/bin/env python3
"""重置账户密码"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount, OperatorAccount, FinanceAccount
from src.core.utils.password import hash_password

async def reset_password(account_type, username, new_password):
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

        # 重置密码
        account.password_hash = hash_password(new_password)
        await session.commit()

        print(f"✅ {type_name}账户密码重置成功！")
        print(f"  用户名: {username}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python reset_password.py <account_type> <username> <new_password>")
        print("account_type: admin, operator, finance")
        sys.exit(1)

    asyncio.run(reset_password(sys.argv[1], sys.argv[2], sys.argv[3]))
