#!/usr/bin/env python3
"""创建运营商账户（从环境变量读取参数）"""
import asyncio
import sys
import os
import secrets
sys.path.insert(0, '/app')

from decimal import Decimal
from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import OperatorAccount
from src.core.utils.password import hash_password

async def create_operator():
    # 从环境变量读取参数
    username = os.environ.get('ACCOUNT_USERNAME')
    password = os.environ.get('ACCOUNT_PASSWORD')
    full_name = os.environ.get('ACCOUNT_FULLNAME')
    email = os.environ.get('ACCOUNT_EMAIL')
    phone = os.environ.get('ACCOUNT_PHONE')
    balance = os.environ.get('ACCOUNT_BALANCE', '1000')

    init_db()
    async with get_db_context() as session:
        # Check if username exists
        result = await session.execute(
            select(OperatorAccount).where(OperatorAccount.username == username)
        )
        if result.scalar_one_or_none():
            print("❌ Username already exists!")
            sys.exit(1)

        # Generate API key
        api_key = secrets.token_urlsafe(32)

        # Create operator
        operator = OperatorAccount(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            email=email,
            phone=phone,
            balance=Decimal(balance),
            api_key=api_key,
            api_key_hash=hash_password(api_key),
            is_active=True,
        )

        session.add(operator)
        await session.commit()

        print("✅ Operator account created successfully!")
        print(f"  Username: {username}")
        print(f"  Full Name: {full_name}")
        print(f"  Initial Balance: ${balance}")
        print(f"  API Key: {api_key}")

if __name__ == "__main__":
    asyncio.run(create_operator())
