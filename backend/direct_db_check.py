#!/usr/bin/env python3
"""直接数据库检查，不依赖项目代码"""

import asyncio
import asyncpg

async def check_db():
    try:
        # 直接连接PostgreSQL
        conn = await asyncpg.connect(
            host='postgres',
            port=5432,
            user='mr_admin',
            password='CHANGE_THIS_PASSWORD',
            database='mr_game_ops'
        )

        print("=== 数据库连接成功 ===")

        # 检查admin_accounts表
        print("\n=== 检查 finance001 用户 ===")
        user = await conn.fetchrow("""
            SELECT id, username, full_name, email, role, is_active,
                   password_hash, created_at, last_login_at
            FROM admin_accounts
            WHERE username = $1
        """, 'finance001')

        if user:
            print("✅ 找到用户:")
            print(f"  ID: {user['id']}")
            print(f"  用户名: {user['username']}")
            print(f"  姓名: {user['full_name']}")
            print(f"  邮箱: {user['email']}")
            print(f"  角色: {user['role']}")
            print(f"  激活: {user['is_active']}")
            print(f"  密码哈希: {user['password_hash'][:50]}...")
            print(f"  创建时间: {user['created_at']}")
            print(f"  最后登录: {user['last_login_at']}")

            # 检查哈希格式
            if user['password_hash'].startswith('$2b$'):
                print("✅ bcrypt哈希格式正确")
            else:
                print("❌ 哈希格式错误")
        else:
            print("❌ 未找到finance001用户")

        # 检查所有财务用户
        print("\n=== 所有财务用户 ===")
        users = await conn.fetch("""
            SELECT username, full_name, email, is_active, created_at
            FROM admin_accounts
            WHERE role = 'finance'
            ORDER BY created_at DESC
        """)

        if users:
            print(f"找到 {len(users)} 个财务用户:")
            for u in users:
                print(f"  - {u['username']} ({u['full_name']}) - {u['email']} - 激活: {u['is_active']}")
        else:
            print("❌ 没有财务用户")

        # 检查最近的用户创建
        print("\n=== 最近创建的用户 ===")
        recent_users = await conn.fetch("""
            SELECT username, role, is_active, created_at
            FROM admin_accounts
            ORDER BY created_at DESC
            LIMIT 10
        """)

        if recent_users:
            print("最近的用户:")
            for u in recent_users:
                print(f"  - {u['username']} ({u['role']}) - {u['is_active']} - {u['created_at']}")

        await conn.close()

    except Exception as e:
        print(f"数据库错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(check_db())