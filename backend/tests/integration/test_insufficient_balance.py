"""集成测试：余额不足场景 (T031)

测试当运营商账户余额不足时的处理流程:
1. 验证HTTP 402状态码返回
2. 验证错误响应包含余额信息
3. 确保数据库未创建使用记录
4. 确保账户余额未变化
5. 测试边界情况(余额刚好不足1分钱)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
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


@pytest.fixture
async def low_balance_data(test_db):
    """准备余额不足的测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_low_balance",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建运营商 - 余额不足
    operator = OperatorAccount(
        username="op_low_balance_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="c" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("30.00"),  # 余额不足(需要50元)
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
        address="测试地址",
        server_identifier="server_low_balance_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_low_balance_001",
        app_name="测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建授权关系
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
async def test_insufficient_balance_returns_402(low_balance_data, test_db):
    """测试余额不足返回HTTP 402状态码

    场景:
    - 余额: 30元
    - 需要: 50元 (5人 × 10元)
    - 预期: HTTP 402 PAYMENT_REQUIRED
    """
    operator = low_balance_data["operator"]
    site = low_balance_data["site"]
    application = low_balance_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'i' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 5  # 需要50元
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    # 验证HTTP状态码
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    # 验证错误响应格式
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error_code"] == "INSUFFICIENT_BALANCE"
    assert "message" in data["detail"]

    # 验证错误消息包含余额信息
    error_message = data["detail"]["message"]
    assert "余额不足" in error_message or "INSUFFICIENT" in error_message.upper()

    # 验证详细信息
    if "details" in data["detail"]:
        details = data["detail"]["details"]
        assert "current_balance" in details
        assert "required_amount" in details
        assert details["current_balance"] == "30.00"
        assert details["required_amount"] == "50.00"


@pytest.mark.asyncio
async def test_insufficient_balance_no_usage_record_created(low_balance_data, test_db):
    """测试余额不足时不创建使用记录"""
    operator = low_balance_data["operator"]
    site = low_balance_data["site"]
    application = low_balance_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'j' * 16}"

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

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    # 验证数据库中没有创建使用记录
    stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
    result = await test_db.execute(stmt)
    usage_record = result.scalar_one_or_none()

    assert usage_record is None, "余额不足时不应创建使用记录"


@pytest.mark.asyncio
async def test_insufficient_balance_no_transaction_created(low_balance_data, test_db):
    """测试余额不足时不创建交易记录"""
    operator = low_balance_data["operator"]
    site = low_balance_data["site"]
    application = low_balance_data["application"]

    # 记录原始交易记录数量
    stmt = select(TransactionRecord).where(
        TransactionRecord.operator_id == operator.id
    )
    result = await test_db.execute(stmt)
    original_transaction_count = len(result.scalars().all())

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'k' * 16}"

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

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    # 验证交易记录数量未增加
    result = await test_db.execute(stmt)
    current_transaction_count = len(result.scalars().all())

    assert current_transaction_count == original_transaction_count, \
        "余额不足时不应创建交易记录"


@pytest.mark.asyncio
async def test_insufficient_balance_account_unchanged(low_balance_data, test_db):
    """测试余额不足时账户余额未变化"""
    operator = low_balance_data["operator"]
    site = low_balance_data["site"]
    application = low_balance_data["application"]

    original_balance = operator.balance

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'l' * 16}"

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

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    # 刷新运营商对象
    await test_db.refresh(operator)

    # 验证余额未变化
    assert operator.balance == original_balance, \
        f"余额不足时账户余额应保持不变: {original_balance} -> {operator.balance}"


@pytest.mark.asyncio
async def test_insufficient_balance_boundary_one_cent_short(test_db):
    """测试边界情况 - 余额刚好差1分钱

    场景:
    - 余额: 49.99元
    - 需要: 50.00元 (5人 × 10元)
    - 差额: 0.01元
    - 预期: HTTP 402
    """
    # 创建管理员
    admin = AdminAccount(
        username="admin_boundary",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建余额刚好差1分钱的运营商
    operator = OperatorAccount(
        username="op_boundary_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="d" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("49.99"),  # 刚好差0.01元
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
        name="边界测试运营点",
        address="测试地址",
        server_identifier="server_boundary_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_boundary_001",
        app_name="边界测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建授权关系
    authorization = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(authorization)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'m' * 16}"

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

    # 验证返回402
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    # 验证余额未变化
    await test_db.refresh(operator)
    assert operator.balance == Decimal("49.99")


@pytest.mark.asyncio
async def test_insufficient_balance_boundary_exact_match(test_db):
    """测试边界情况 - 余额刚好等于所需金额

    场景:
    - 余额: 50.00元
    - 需要: 50.00元 (5人 × 10元)
    - 差额: 0元
    - 预期: HTTP 200 OK (授权成功)
    """
    # 创建管理员
    admin = AdminAccount(
        username="admin_exact",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建余额刚好够的运营商
    operator = OperatorAccount(
        username="op_exact_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="e" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("50.00"),  # 刚好够
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
        name="精确测试运营点",
        address="测试地址",
        server_identifier="server_exact_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_exact_001",
        app_name="精确测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建授权关系
    authorization = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(authorization)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'n' * 16}"

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

    # 验证授权成功
    assert response.status_code == status.HTTP_200_OK

    # 验证余额变为0
    await test_db.refresh(operator)
    assert operator.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_insufficient_balance_zero_balance(test_db):
    """测试边界情况 - 余额为0

    场景:
    - 余额: 0.00元
    - 需要: 20.00元 (2人 × 10元)
    - 预期: HTTP 402
    """
    # 创建管理员
    admin = AdminAccount(
        username="admin_zero",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.flush()

    # 创建余额为0的运营商
    operator = OperatorAccount(
        username="op_zero_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="f" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("0.00"),  # 余额为0
        customer_tier="trial",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(operator)
    await test_db.flush()

    # 创建运营点
    site = OperationSite(
        operator_id=operator.id,
        name="零余额测试运营点",
        address="测试地址",
        server_identifier="server_zero_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_zero_001",
        app_name="零余额测试游戏",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(application)
    await test_db.flush()

    # 创建授权关系
    authorization = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=application.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(authorization)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'o' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 2  # 最小玩家数
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    # 验证返回402
    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED

    # 验证余额仍为0
    await test_db.refresh(operator)
    assert operator.balance == Decimal("0.00")
