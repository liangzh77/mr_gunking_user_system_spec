#!/usr/bin/env python3
"""检查财务用户是否存在"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def check_finance_user():
    """检查财务用户"""

    # 数据库连接
    db_url = 'postgresql+asyncpg://mr_admin:CHANGE_THIS_PASSWORD@postgres:5432/mr_game_ops'
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查admin_accounts表中的finance001用户
            print("=== 检查 admin_accounts 表中的 finance001 用户 ===")
            result = await session.execute(
                text("""
                    SELECT id, username, full_name, email, role, is_active,
                           password_hash, created_at, last_login_at
                    FROM admin_accounts
                    WHERE username = :username
                """),
                {'username': 'finance001'}
            )
            user = result.fetchone()

            if user:
                print(f"✅ 找到用户:")
                print(f"  ID: {user.id}")
                print(f"  用户名: {user.username}")
                print(f"  姓名: {user.full_name}")
                print(f"  邮箱: {user.email}")
                print(f"  角色: {user.role}")
                print(f"  是否激活: {user.is_active}")
                print(f"  密码哈希: {user.password_hash[:50]}...")
                print(f"  创建时间: {user.created_at}")
                print(f"  最后登录: {user.last_login_at}")
                print()

                # 验证密码哈希格式
                if user.password_hash.startswith('$2b$'):
                    print("✅ 密码哈希格式正确 (bcrypt)")
                else:
                    print("❌ 密码哈希格式错误")
                    print(f"   实际格式: {user.password_hash[:10]}...")

                # 检查角色是否为finance
                if user.role == 'finance':
                    print("✅ 用户角色为 finance")
                else:
                    print(f"❌ 用户角色错误: {user.role}")

                # 检查是否激活
                if user.is_active:
                    print("✅ 用户账户已激活")
                else:
                    print("❌ 用户账户未激活")

            else:
                print("❌ 未找到 finance001 用户")

            print()

            # 检查admin_accounts表中的所有财务角色用户
            print("=== 检查所有财务角色用户 ===")
            result = await session.execute(
                text("""
                    SELECT id, username, full_name, email, role, is_active, created_at
                    FROM admin_accounts
                    WHERE role = 'finance'
                    ORDER BY created_at DESC
                """)
            )
            finance_users = result.fetchall()

            if finance_users:
                print(f"找到 {len(finance_users)} 个财务用户:")
                for user in finance_users:
                    print(f"  - {user.username} ({user.full_name}) - {user.email} - 激活: {user.is_active}")
            else:
                print("❌ 没有找到任何财务角色用户")

            print()

            # 检查finance_accounts表
            print("=== 检查 finance_accounts 表 ===")
            try:
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM finance_accounts
                    """)
                )
                count = result.fetchone().count
                print(f"finance_accounts 表中有 {count} 条记录")

                if count > 0:
                    result = await session.execute(
                        text("""
                            SELECT id, username, full_name, role, is_active
                            FROM finance_accounts
                            ORDER BY created_at DESC
                            LIMIT 5
                        """)
                    )
                    users = result.fetchall()
                    print("finance_accounts 表中的用户:")
                    for user in users:
                        print(f"  - {user.username} ({user.full_name}) - {user.role} - 激活: {user.is_active}")

            except Exception as e:
                print(f"查询 finance_accounts 表失败: {e}")

            print()

            # 测试密码验证
            print("=== 测试密码验证 ===")
            if user:
                from src.core.utils.password import verify_password

                test_password = "Pass@2024!"
                if verify_password(test_password, user.password_hash):
                    print("✅ 密码验证通过")
                else:
                    print("❌ 密码验证失败")
                    print("   尝试其他可能的密码...")

                    # 尝试一些其他可能的密码
                    other_passwords = [
                        "Pass@2024",
                        "Pass2024!",
                        "pass@2024!",
                        "Finance001",
                        "finance001"
                    ]

                    for pwd in other_passwords:
                        if verify_password(pwd, user.password_hash):
                            print(f"✅ 正确密码可能是: {pwd}")
                            break
                    else:
                        print("❌ 尝试的密码都不匹配")

    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(check_finance_user())