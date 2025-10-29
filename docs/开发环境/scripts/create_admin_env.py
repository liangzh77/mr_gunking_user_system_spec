#!/usr/bin/env python3
"""创建管理员账户（从环境变量读取参数）"""
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount
from src.core.utils.password import hash_password

async def create_admin():
    # 从环境变量读取参数
    username = os.environ.get('ACCOUNT_USERNAME')
    password = os.environ.get('ACCOUNT_PASSWORD')
    full_name = os.environ.get('ACCOUNT_FULLNAME')
    email = os.environ.get('ACCOUNT_EMAIL')
    phone = os.environ.get('ACCOUNT_PHONE')
    role = os.environ.get('ACCOUNT_ROLE', 'admin')

    init_db()
    async with get_db_context() as session:
        # Check if username exists
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == username)
        )
        if result.scalar_one_or_none():
            print("❌ Username already exists!")
            sys.exit(1)

        # Create admin
        admin = AdminAccount(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            email=email,
            phone=phone,
            role=role,
            permissions=[],
            is_active=True,
        )

        session.add(admin)
        await session.commit()

        print("✅ Admin account created successfully!")
        print(f"  Username: {username}")
        print(f"  Full Name: {full_name}")
        print(f"  Role: {role}")

if __name__ == "__main__":
    asyncio.run(create_admin())
