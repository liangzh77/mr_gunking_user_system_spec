#!/usr/bin/env python3
"""创建财务账户"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import FinanceAccount
from src.core.utils.password import hash_password

async def create_finance(username, password, full_name, email, phone, role):
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否存在
        result = await session.execute(
            select(FinanceAccount).where(FinanceAccount.username == username)
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在！")
            sys.exit(1)

        # 创建财务账户
        finance = FinanceAccount(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            email=email,
            phone=phone,
            role=role,
            permissions=[],
            is_active=True,
        )

        session.add(finance)
        await session.commit()

        print("✅ 财务账户创建成功！")
        print(f"  用户名: {username}")
        print(f"  姓名: {full_name}")
        print(f"  角色: {role}")

if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("Usage: python create_finance.py <username> <password> <full_name> <email> <phone> <role>")
        sys.exit(1)

    asyncio.run(create_finance(
        sys.argv[1],  # username
        sys.argv[2],  # password
        sys.argv[3],  # full_name
        sys.argv[4],  # email
        sys.argv[5],  # phone
        sys.argv[6],  # role
    ))
