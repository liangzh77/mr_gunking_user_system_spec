#!/usr/bin/env python3
"""修改管理员密码"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.core.utils.password import hash_password

async def change_password(username: str, new_password: str):
    """修改管理员密码"""

    db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查用户是否存在
            result = await session.execute(
                text("SELECT id, full_name FROM admin_accounts WHERE username = :username"),
                {'username': username}
            )
            user = result.fetchone()

            if not user:
                print(f'错误：用户 {username} 不存在')
                return False

            # 更新密码
            password_hash = hash_password(new_password)

            await session.execute(text('''
                UPDATE admin_accounts
                SET password_hash = :password_hash,
                    updated_at = NOW()
                WHERE username = :username
            '''), {
                'password_hash': password_hash,
                'username': username
            })

            await session.commit()
            print(f'密码修改成功！')
            print(f'用户名: {username}')
            print(f'新密码: {new_password}')
            return True

    except Exception as e:
        print(f'修改失败: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print('用法: python change_admin_password.py <用户名> <新密码>')
        print('示例: python change_admin_password.py admin NewSecurePassword123!')
        sys.exit(1)

    username = sys.argv[1]
    new_password = sys.argv[2]

    asyncio.run(change_password(username, new_password))
