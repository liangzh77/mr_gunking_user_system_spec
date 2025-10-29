#!/usr/bin/env python3
"""修改管理员角色"""
import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models import AdminAccount

async def change_admin_role(username, new_role):
    init_db()
    async with get_db_context() as session:
        # 查询管理员
        result = await session.execute(
            select(AdminAccount).where(AdminAccount.username == username)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ 管理员不存在！")
            sys.exit(1)

        old_role = admin.role

        # 修改角色
        admin.role = new_role
        await session.commit()

        print("✅ 管理员角色修改成功！")
        print(f"  用户名: {username}")
        print(f"  原角色: {old_role}")
        print(f"  新角色: {new_role}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python change_admin_role.py <username> <new_role>")
        print("new_role: super_admin, admin")
        sys.exit(1)

    asyncio.run(change_admin_role(sys.argv[1], sys.argv[2]))
