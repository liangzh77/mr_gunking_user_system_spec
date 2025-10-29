#!/usr/bin/env python3
"""创建运营商账户"""
import asyncio
import sys
import secrets
sys.path.insert(0, '/app')

from decimal import Decimal
from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def create_operator(username, password, full_name, email, phone, initial_balance):
    init_db()
    async with get_db_context() as session:
        # 检查用户名是否存在
        result = await session.execute(
            select(OperatorAccount).where(OperatorAccount.username == username)
        )
        if result.scalar_one_or_none():
            print("❌ 用户名已存在！")
            sys.exit(1)

        # 生成API密钥
        api_key = secrets.token_urlsafe(32)

        # 创建运营商
        operator = OperatorAccount(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            email=email,
            phone=phone,
            balance=Decimal(str(initial_balance)),
            api_key=api_key,
            api_key_hash=hash_password(api_key),
            is_active=True,
        )

        session.add(operator)
        await session.commit()

        print("✅ 运营商账户创建成功！")
        print(f"  用户名: {username}")
        print(f"  姓名: {full_name}")
        print(f"  初始余额: ¥{initial_balance}")
        print(f"  API密钥: {api_key}")
        print("")
        print("⚠️  请妥善保存API密钥，它只会显示一次！")

if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("Usage: python create_operator.py <username> <password> <full_name> <email> <phone> <initial_balance>")
        sys.exit(1)

    asyncio.run(create_operator(
        sys.argv[1],  # username
        sys.argv[2],  # password
        sys.argv[3],  # full_name
        sys.argv[4],  # email
        sys.argv[5],  # phone
        sys.argv[6],  # initial_balance
    ))
