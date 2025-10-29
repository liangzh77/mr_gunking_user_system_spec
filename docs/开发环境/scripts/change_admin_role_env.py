#!/usr/bin/env python3
"""修改管理员角色（从环境变量读取参数）"""
import asyncio
import sys
import os
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount

async def change_admin_role():
    # 从环境变量读取参数
    username = os.environ.get('ACCOUNT_USERNAME')
    new_role = os.environ.get('ACCOUNT_ROLE')

    init_db()
    async with get_db_context() as session:
        # Query admin
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == username)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ Admin account not found!")
            sys.exit(1)

        old_role = admin.role

        # Change role
        admin.role = new_role
        await session.commit()

        print("✅ Admin role changed successfully!")
        print(f"  Username: {username}")
        print(f"  Old Role: {old_role}")
        print(f"  New Role: {new_role}")

if __name__ == "__main__":
    asyncio.run(change_admin_role())
