#!/usr/bin/env python
"""测试密码哈希和验证"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from src.core.config import get_settings
from src.core.utils.password import hash_password, verify_password
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount


async def test_passwords():
    """测试密码哈希和验证"""
    print("="*60)
    print("密码哈希和验证测试")
    print("="*60)
    print()

    # 测试 1: 基本哈希和验证
    print("测试 1: 基本密码哈希和验证")
    test_password = "Test123!@#"
    hashed = hash_password(test_password)
    print(f"  原密码: {test_password}")
    print(f"  哈希: {hashed[:60]}...")
    print(f"  验证正确密码: {verify_password(test_password, hashed)}")
    print(f"  验证错误密码: {verify_password('WrongPassword', hashed)}")
    print()

    # 测试 2: 查询数据库中的账户
    print("测试 2: 数据库账户密码验证")
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 测试运营商账户
            result = await session.execute(
                select(OperatorAccount).where(OperatorAccount.username == "test_operator_1")
            )
            operator = result.scalar_one_or_none()

            if operator:
                print(f"  运营商账户: {operator.username}")
                print(f"  密码哈希: {operator.password_hash[:60]}...")
                print(f"  验证 'Test123!@#': {verify_password('Test123!@#', operator.password_hash)}")
                print(f"  is_active: {operator.is_active}")
                print(f"  deleted_at: {operator.deleted_at}")
            else:
                print("  ❌ 未找到 test_operator_1")
            print()

            # 测试管理员账户
            result = await session.execute(
                select(AdminAccount).where(AdminAccount.username == "admin_test")
            )
            admin = result.scalar_one_or_none()

            if admin:
                print(f"  管理员账户: {admin.username}")
                print(f"  密码哈希: {admin.password_hash[:60]}...")
                print(f"  验证 'Admin123!@#': {verify_password('Admin123!@#', admin.password_hash)}")
                print(f"  is_active: {admin.is_active}")
                print(f"  permissions type: {type(admin.permissions)}")
                print(f"  permissions value: {admin.permissions}")
            else:
                print("  ❌ 未找到 admin_test")

    finally:
        await engine.dispose()

    print()
    print("="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_passwords())
