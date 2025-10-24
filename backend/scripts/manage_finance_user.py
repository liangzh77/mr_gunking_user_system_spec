#!/usr/bin/env python3
"""管理财务用户账号"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from src.core.utils.password import hash_password

async def create_finance_user(username: str, password: str, full_name: str, email: str = None, phone: str = None):
    """创建财务用户"""

    db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查用户是否已存在
            result = await session.execute(
                text("SELECT COUNT(*) FROM admin_accounts WHERE username = :username"),
                {'username': username}
            )
            count = result.scalar()

            if count > 0:
                print(f'错误：用户 {username} 已存在')
                return False

            # 创建财务用户
            user_id = str(uuid.uuid4())
            password_hash = hash_password(password)
            current_time = datetime.utcnow()

            # 财务角色权限：只能访问财务相关功能
            finance_permissions = [
                "finance:read",
                "finance:recharge",
                "finance:refund",
                "invoice:read",
                "invoice:create",
                "statistics:read"
            ]

            await session.execute(text('''
                INSERT INTO admin_accounts (
                    id, username, password_hash, full_name, email, phone,
                    role, permissions, is_active, created_at, updated_at
                ) VALUES (
                    :id, :username, :password_hash, :full_name, :email, :phone,
                    :role, :permissions, :is_active, :created_at, :updated_at
                )
            '''), {
                'id': user_id,
                'username': username,
                'password_hash': password_hash,
                'full_name': full_name,
                'email': email or f'{username}@mrgameops.com',
                'phone': phone or '13800138000',
                'role': 'finance',
                'permissions': str(finance_permissions),
                'is_active': True,
                'created_at': current_time,
                'updated_at': current_time
            })

            await session.commit()
            print('财务用户创建成功！')
            print(f'用户名: {username}')
            print(f'密码: {password}')
            print(f'姓名: {full_name}')
            print(f'角色: finance（财务）')
            print(f'权限: {", ".join(finance_permissions)}')
            return True

    except Exception as e:
        print(f'创建失败: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

async def update_finance_password(username: str, new_password: str):
    """修改财务用户密码"""

    db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查用户是否存在且为财务角色
            result = await session.execute(
                text("SELECT id, full_name, role FROM admin_accounts WHERE username = :username"),
                {'username': username}
            )
            user = result.fetchone()

            if not user:
                print(f'错误：用户 {username} 不存在')
                return False

            if user.role != 'finance':
                print(f'警告：用户 {username} 不是财务角色（当前角色: {user.role}）')
                print('仍将修改密码...')

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

async def list_users():
    """列出所有用户"""

    db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            result = await session.execute(
                text("""
                    SELECT username, full_name, role, email, is_active, created_at
                    FROM admin_accounts
                    ORDER BY created_at DESC
                """)
            )
            users = result.fetchall()

            if not users:
                print('没有找到用户')
                return

            print('\n当前用户列表：')
            print('-' * 100)
            print(f'{"用户名":<15} {"姓名":<15} {"角色":<15} {"邮箱":<25} {"状态":<8} 创建时间')
            print('-' * 100)

            for user in users:
                status = '激活' if user.is_active else '禁用'
                created = user.created_at.strftime('%Y-%m-%d %H:%M:%S')
                print(f'{user.username:<15} {user.full_name:<15} {user.role:<15} {user.email:<25} {status:<8} {created}')

            print('-' * 100)
            print(f'总计: {len(users)} 个用户\n')

    except Exception as e:
        print(f'查询失败: {e}')
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('用法:')
        print('  1. 创建财务用户:')
        print('     python manage_finance_user.py create <用户名> <密码> <姓名> [邮箱] [手机]')
        print('     示例: python manage_finance_user.py create finance001 Pass123! 张财务 zhang@example.com 13800138001')
        print('')
        print('  2. 修改财务用户密码:')
        print('     python manage_finance_user.py password <用户名> <新密码>')
        print('     示例: python manage_finance_user.py password finance001 NewPass456!')
        print('')
        print('  3. 列出所有用户:')
        print('     python manage_finance_user.py list')
        sys.exit(1)

    command = sys.argv[1]

    if command == 'create':
        if len(sys.argv) < 5:
            print('错误：创建用户需要至少4个参数')
            print('用法: python manage_finance_user.py create <用户名> <密码> <姓名> [邮箱] [手机]')
            sys.exit(1)

        username = sys.argv[2]
        password = sys.argv[3]
        full_name = sys.argv[4]
        email = sys.argv[5] if len(sys.argv) > 5 else None
        phone = sys.argv[6] if len(sys.argv) > 6 else None

        asyncio.run(create_finance_user(username, password, full_name, email, phone))

    elif command == 'password':
        if len(sys.argv) != 4:
            print('错误：修改密码需要2个参数')
            print('用法: python manage_finance_user.py password <用户名> <新密码>')
            sys.exit(1)

        username = sys.argv[2]
        new_password = sys.argv[3]

        asyncio.run(update_finance_password(username, new_password))

    elif command == 'list':
        asyncio.run(list_users())

    else:
        print(f'错误：未知命令 "{command}"')
        print('可用命令: create, password, list')
        sys.exit(1)
