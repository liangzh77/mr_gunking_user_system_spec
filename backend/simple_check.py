#!/usr/bin/env python3
"""简单检查财务用户"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check_user():
    try:
        # 使用正确的数据库连接
        db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
        engine = create_async_engine(db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # 检查finance001用户
            result = await session.execute(
                text("SELECT username, role, is_active, LENGTH(password_hash) as hash_len FROM admin_accounts WHERE username = 'finance001'")
            )
            user = result.fetchone()

            if user:
                print(f"用户: {user.username}")
                print(f"角色: {user.role}")
                print(f"激活状态: {user.is_active}")
                print(f"密码哈希长度: {user.hash_len}")

                # 检查所有财务用户
                result = await session.execute(
                    text("SELECT username, role, is_active FROM admin_accounts WHERE role = 'finance'")
                )
                users = result.fetchall()
                print(f"\n所有财务用户: {[u.username for u in users]}")
            else:
                print("❌ finance001 用户不存在")

                # 显示所有用户
                result = await session.execute(
                    text("SELECT username, role, is_active FROM admin_accounts ORDER BY created_at DESC LIMIT 10")
                )
                users = result.fetchall()
                print("最近的用户:")
                for u in users:
                    print(f"  - {u.username} ({u.role}) - 激活: {u.is_active}")

            await engine.dispose()

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(check_user())