"""集成测试：完整授权流程 (T030)

测试完整的游戏授权流程:
1. API Key验证
2. 会话ID格式和幂等性验证
3. 运营点归属验证
4. 应用授权状态验证
5. 玩家数量验证
6. 余额扣费
7. 返回授权Token

测试范围: API → Service → Repository → Database
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy import select
from fastapi import status

from src.main import app
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.authorization import OperatorAppAuthorization
from src.models.usage_record import UsageRecord
from src.models.transaction import TransactionRecord
from src.db.session import get_db


@pytest.fixture
async def test_data(test_db):
    """准备测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_test",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建运营商
    operator = OperatorAccount(
        username="op_test_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="a" * 64,  # 64位API Key
        api_key_hash="hashed_secret",
        balance=Decimal("500.00"),  # 充足余额
        customer_tier="standard",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(operator)
    await test_db.flush()

    # 创建运营点
    site = OperationSite(
        operator_id=operator.id,
        name="测试运营点",
        address="北京市朝阳区测试街道1号",
        server_identifier="server_test_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_test_001",
        app_name="测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建运营商-应用授权关系
    authorization = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(authorization)
    await test_db.commit()

    return {
        "admin": admin,
        "operator": operator,
        "site": site,
        "application": application,
        "authorization": authorization
    }


@pytest.mark.asyncio
async def test_complete_authorization_flow_success(test_data, test_db):
    """测试完整授权流程 - 成功场景

    流程:
    1. 发送授权请求(正确的API Key + 会话ID + 请求体)
    2. 系统验证通过
    3. 扣除余额(5人 × 10元 = 50元)
    4. 创建使用记录和交易记录
    5. 返回授权Token
    """
    operator = test_data["operator"]
    site = test_data["site"]
    application = test_data["application"]

    # 生成会话ID (格式: {operatorId}_{timestamp}_{random16})
    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'a' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 5
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    # 验证响应状态码
    assert response.status_code == status.HTTP_200_OK

    # 验证响应结构
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    response_data = data["data"]
    assert "authorization_token" in response_data
    assert response_data["session_id"] == session_id
    assert response_data["app_name"] == application.app_name
    assert response_data["player_count"] == 5
    assert response_data["unit_price"] == "10.00"
    assert response_data["total_cost"] == "50.00"
    assert response_data["balance_after"] == "450.00"  # 500 - 50
    assert "authorized_at" in response_data

    # 验证数据库 - 使用记录
    stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
    result = await test_db.execute(stmt)
    usage_record = result.scalar_one_or_none()

    assert usage_record is not None
    assert usage_record.operator_id == operator.id
    assert usage_record.site_id == site.id
    assert usage_record.application_id == application.id
    assert usage_record.player_count == 5
    assert usage_record.price_per_player == Decimal("10.00")
    assert usage_record.total_cost == Decimal("50.00")
    assert usage_record.authorization_token == response_data["authorization_token"]

    # 验证数据库 - 交易记录
    stmt = select(TransactionRecord).where(
        TransactionRecord.operator_id == operator.id,
        TransactionRecord.related_usage_id == usage_record.id
    )
    result = await test_db.execute(stmt)
    transaction_record = result.scalar_one_or_none()

    assert transaction_record is not None
    assert transaction_record.transaction_type == "consumption"
    assert transaction_record.amount == Decimal("-50.00")
    assert transaction_record.balance_before == Decimal("500.00")
    assert transaction_record.balance_after == Decimal("450.00")

    # 验证数据库 - 运营商余额更新
    await test_db.refresh(operator)
    assert operator.balance == Decimal("450.00")


@pytest.mark.asyncio
async def test_authorization_flow_with_minimum_players(test_data, test_db):
    """测试授权流程 - 最小玩家数(2人)"""
    operator = test_data["operator"]
    site = test_data["site"]
    application = test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'b' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 2  # 最小值
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["data"]["player_count"] == 2
    assert data["data"]["total_cost"] == "20.00"  # 2 × 10


@pytest.mark.asyncio
async def test_authorization_flow_with_maximum_players(test_data, test_db):
    """测试授权流程 - 最大玩家数(8人)"""
    operator = test_data["operator"]
    site = test_data["site"]
    application = test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'c' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 8  # 最大值
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["data"]["player_count"] == 8
    assert data["data"]["total_cost"] == "80.00"  # 8 × 10


@pytest.mark.asyncio
async def test_authorization_flow_invalid_api_key(test_data):
    """测试授权流程 - 无效API Key"""
    site = test_data["site"]
    application = test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"invalid_op_{current_timestamp}_{'d' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 5
            },
            headers={
                "X-API-Key": "invalid_api_key_64chars" + "x" * 42,  # 64位但不存在
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert data["detail"]["error_code"] == "INVALID_API_KEY"


@pytest.mark.asyncio
async def test_authorization_flow_locked_account(test_data, test_db):
    """测试授权流程 - 账户已锁定"""
    operator = test_data["operator"]
    site = test_data["site"]
    application = test_data["application"]

    # 锁定账户
    operator.is_locked = True
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'e' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 5
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["detail"]["error_code"] == "ACCOUNT_LOCKED"

    # 恢复账户状态
    operator.is_locked = False
    await test_db.commit()


@pytest.mark.asyncio
async def test_authorization_flow_inactive_application(test_data, test_db):
    """测试授权流程 - 应用已停用"""
    operator = test_data["operator"]
    site = test_data["site"]
    application = test_data["application"]

    # 停用应用
    application.is_active = False
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'f' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 5
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["detail"]["error_code"] == "APP_INACTIVE"

    # 恢复应用状态
    application.is_active = True
    await test_db.commit()


@pytest.mark.asyncio
async def test_authorization_flow_unauthorized_application(test_data, test_db):
    """测试授权流程 - 运营商未授权访问该应用"""
    operator = test_data["operator"]
    site = test_data["site"]
    admin = test_data["admin"]

    # 创建另一个应用(未授权给该运营商)
    unauthorized_app = Application(
        app_code="app_unauthorized_001",
        app_name="未授权游戏",
        price_per_player=Decimal("15.00"),
        min_players=2,
        max_players=6,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(unauthorized_app)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'g' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(unauthorized_app.id),
                "site_id": str(site.id),
                "player_count": 5
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["detail"]["error_code"] == "APP_NOT_AUTHORIZED"


@pytest.mark.asyncio
async def test_authorization_flow_site_not_owned(test_data, test_db):
    """测试授权流程 - 运营点不属于该运营商"""
    operator = test_data["operator"]
    application = test_data["application"]
    admin = test_data["admin"]

    # 创建另一个运营商及其运营点
    another_operator = OperatorAccount(
        username="op_another_001",
        full_name="Another Operator",  # 必填字段
        email="another@test.com",
        phone="13800138001",
        password_hash="hashed_password",
        api_key="b" * 64,
        api_key_hash="hashed_secret_2",
        balance=Decimal("300.00"),
        customer_tier="standard",
        is_active=True,
        created_by=admin.id
    )
    test_db.add(another_operator)
    await test_db.flush()

    another_site = OperationSite(
        operator_id=another_operator.id,
        name="其他运营点",
        address="上海市浦东新区测试路2号",  # 必填字段
        server_identifier="server_another_001",
        is_active=True
    )
    test_db.add(another_site)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'h' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(another_site.id),  # 不属于当前运营商
                "player_count": 5
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    data = response.json()
    assert data["detail"]["error_code"] == "SITE_NOT_OWNED"
