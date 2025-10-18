#!/usr/bin/env python
"""
批量创建性能测试账户

创建 100 个运营商测试账户用于 Locust 性能测试
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.core.config import get_settings
from src.core.utils.password import hash_password
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
import uuid
from datetime import datetime, timezone
import secrets


async def create_test_operators(session: AsyncSession, count: int = 100):
    """创建测试运营商账户"""
    print(f"创建 {count} 个运营商测试账户...")

    created = 0
    for i in range(1, count + 1):
        username = f"test_operator_{i}"

        # 检查是否已存在
        from sqlalchemy import select
        result = await session.execute(
            select(OperatorAccount).where(OperatorAccount.username == username)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  [跳过] {username} 已存在")
            continue

        # 生成 API Key
        api_key = f"test_key_{secrets.token_urlsafe(32)}"
        api_key_hash = hash_password(api_key)

        # 创建账户
        operator = OperatorAccount(
            id=uuid.uuid4(),
            username=username,
            password_hash=hash_password("Test123!@#"),
            full_name=f"测试运营商{i}",
            phone=f"138{i:08d}",
            email=f"test_operator_{i}@example.com",
            api_key=api_key,
            api_key_hash=api_key_hash,
            balance=1000.00,  # 初始余额 1000 元
            customer_tier="standard",  # vip | standard | trial
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(operator)
        created += 1

        if i % 10 == 0:
            print(f"  [进度] 已创建 {i}/{count} 个账户")

    await session.commit()
    print(f"✅ 成功创建 {created} 个运营商测试账户")
    return created


async def create_test_admin(session: AsyncSession):
    """创建测试管理员账户"""
    print("创建管理员测试账户...")

    username = "admin_test"

    # 检查是否已存在
    from sqlalchemy import select
    result = await session.execute(
        select(AdminAccount).where(AdminAccount.username == username)
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"  [跳过] {username} 已存在")
        return 0

    # 创建账户
    admin = AdminAccount(
        id=uuid.uuid4(),
        username=username,
        password_hash=hash_password("Admin123!@#"),
        full_name="测试管理员",
        email="admin_test@example.com",
        role="super_admin",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    session.add(admin)
    await session.commit()

    print(f"✅ 成功创建管理员测试账户: {username}")
    return 1


async def main():
    """主函数"""
    print("="*60)
    print("MR 游戏运营管理系统 - 创建性能测试账户")
    print("="*60)
    print()

    # 获取配置
    settings = get_settings()

    # 创建数据库引擎
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )

    # 创建会话
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with async_session() as session:
            # 创建运营商测试账户
            operator_count = await create_test_operators(session, count=100)

            print()

            # 创建管理员测试账户
            admin_count = await create_test_admin(session)

            print()
            print("="*60)
            print(f"✅ 测试账户创建完成")
            print(f"   - 运营商账户: {operator_count} 个")
            print(f"   - 管理员账户: {admin_count} 个")
            print("="*60)
            print()
            print("账户信息:")
            print("  运营商账户:")
            print("    用户名: test_operator_1 到 test_operator_100")
            print("    密码:   Test123!@#")
            print("    余额:   1000.00 元")
            print()
            print("  管理员账户:")
            print("    用户名: admin_test")
            print("    密码:   Admin123!@#")
            print()
            print("现在可以运行 Locust 性能测试了！")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await engine.dispose()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
