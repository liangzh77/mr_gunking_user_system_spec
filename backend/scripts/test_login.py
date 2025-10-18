#!/usr/bin/env python
"""直接测试登录服务"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.core.config import get_settings
from src.services.operator import OperatorService
from src.services.admin_auth import AdminAuthService


async def test_operator_login():
    """测试运营商登录"""
    print("="*60)
    print("测试运营商登录")
    print("="*60)
    print()

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            service = OperatorService(session)

            print("尝试登录: username='test_operator_1', password='Test123!@#'")
            try:
                response = await service.login(
                    username="test_operator_1",
                    password="Test123!@#",
                    login_ip="127.0.0.1"
                )
                print(f"SUCCESS: Login successful!")
                print(f"  Access Token: {response.data.access_token[:50]}...")
                print(f"  Operator ID: {response.data.operator.operator_id}")
                print(f"  Username: {response.data.operator.username}")
                print(f"  Category: {response.data.operator.category}")
            except Exception as e:
                print(f"FAILED: Login failed: {e}")
                import traceback
                traceback.print_exc()

    finally:
        await engine.dispose()

    print()


async def test_admin_login():
    """测试管理员登录"""
    print("="*60)
    print("测试管理员登录")
    print("="*60)
    print()

    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            service = AdminAuthService(session)

            print("尝试登录: username='admin_test', password='Admin123!@#'")
            try:
                response = await service.login(
                    username="admin_test",
                    password="Admin123!@#",
                    login_ip="127.0.0.1"
                )
                print(f"SUCCESS: Login successful!")
                print(f"  Access Token: {response.access_token[:50]}...")
                print(f"  Username: {response.user.username}")
                print(f"  Role: {response.user.role}")
                print(f"  Permissions type: {type(response.user.permissions)}")
                print(f"  Permissions value: {response.user.permissions}")
            except Exception as e:
                print(f"FAILED: Login failed: {e}")
                import traceback
                traceback.print_exc()

    finally:
        await engine.dispose()

    print()


async def main():
    await test_operator_login()
    await test_admin_login()


if __name__ == "__main__":
    asyncio.run(main())
