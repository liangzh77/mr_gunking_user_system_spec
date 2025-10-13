"""Pytest配置和共享fixtures

此文件定义所有测试通用的fixtures和配置。
"""

import asyncio
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects import postgresql
from sqlalchemy import TypeDecorator, String, event
import uuid

from src.db.base import Base
from src.core.config import get_settings

# 导入所有模型以便SQLAlchemy创建表
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.authorization import OperatorAppAuthorization
from src.models.usage_record import UsageRecord
from src.models.transaction import TransactionRecord


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # 使用内存数据库进行测试


# UUID类型适配器 - 将PostgreSQL UUID映射到SQLite String
class GUID(TypeDecorator):
    """平台无关的GUID类型

    在PostgreSQL中使用UUID类型,在SQLite中使用CHAR(36)存储
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.UUID())
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环供整个测试会话使用"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎(会话级别,复用)"""
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    from sqlalchemy import JSON

    # 替换PostgreSQL特定类型为SQLite兼容类型
    def replace_postgres_types(metadata):
        """替换PostgreSQL特定类型为SQLite兼容类型"""
        for table in metadata.tables.values():
            for column in table.columns:
                # 检查类型名称
                type_class_name = column.type.__class__.__name__

                # 替换UUID类型
                if 'UUID' in type_class_name or isinstance(column.type, PG_UUID):
                    column.type = GUID()

                # 替换JSONB为JSON (SQLite支持JSON)
                elif isinstance(column.type, JSONB):
                    column.type = JSON()

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,  # 使用StaticPool确保内存数据库在所有连接间共享
        connect_args={"check_same_thread": False},  # SQLite允许多线程访问
    )

    # 在创建表之前替换PostgreSQL特定类型
    replace_postgres_types(Base.metadata)

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 清理:删除所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话(每个测试函数独立事务)

    使用方式:
    ```python
    async def test_something(test_db):
        # test_db是一个AsyncSession对象
        result = await test_db.execute(select(User))
        ...
    ```
    """
    # 创建session factory
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # 开始事务
    async with async_session() as session:
        async with session.begin():
            yield session
            # 测试结束后自动回滚
            await session.rollback()


@pytest.fixture(autouse=True, scope="function")
async def reset_database(test_engine):
    """每个测试后重置数据库(清空所有表)

    autouse=True 表示自动应用于所有测试
    """
    # 测试前确保表存在
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 测试后清空所有表数据 (但不删除表结构)
    # 注意：SQLite内存数据库在session作用域内共享
    # 不需要drop表，只需要清空数据即可


@pytest.fixture
def create_admin_defaults():
    """提供创建AdminAccount的默认值"""
    return {
        "full_name": "Test Admin",
        "email": "admin@test.com",
        "phone": "13800138000",
    }


@pytest.fixture
def create_operator_defaults():
    """提供创建OperatorAccount的默认值"""
    return {
        "full_name": "Test Operator",
        "email": "operator@test.com",
        "phone": "13900139000",
        "password_hash": "hashed_password_here",
    }


# Pytest markers配置
def pytest_configure(config):
    """配置自定义markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "contract: Contract tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")
