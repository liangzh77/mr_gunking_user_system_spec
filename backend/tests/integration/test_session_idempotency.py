"""集成测试：会话ID幂等性 (T032)

测试会话ID的幂等性保护机制,防止重复扣费:
1. 相同会话ID第二次请求返回已有授权信息
2. 不重复扣费
3. 不创建重复使用记录
4. 不创建重复交易记录
5. HTTP状态码应为200或409(取决于实现策略)
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
async def idempotency_test_data(test_db):
    """准备幂等性测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_idempotency",
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
        username="op_idempotency_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="g" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("500.00"),
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
        name="幂等性测试运营点",
        address="测试地址",
        server_identifier="server_idempotency_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_idempotency_001",
        app_name="幂等性测试游戏",
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
async def test_duplicate_session_id_returns_same_authorization(idempotency_test_data, test_db):
    """测试重复会话ID返回相同的授权信息

    流程:
    1. 第一次请求成功授权
    2. 使用相同会话ID再次请求
    3. 验证返回相同的authorization_token
    4. 验证响应数据一致
    """
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'p' * 16}"

    request_payload = {
        "app_id": str(application.id),
        "site_id": str(site.id),
        "player_count": 5
    }

    headers = {
        "X-API-Key": operator.api_key,
        "X-Signature": "test_signature",
        "X-Timestamp": str(current_timestamp),
        "X-Session-ID": session_id
    }

    # 第一次请求
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    first_auth_token = data1["data"]["authorization_token"]
    first_balance_after = data1["data"]["balance_after"]

    # 第二次请求(相同会话ID)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response2 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    # 验证第二次请求成功(幂等性保护)
    # 可能返回200(返回已有授权)或409(明确标识幂等冲突)
    assert response2.status_code in [status.HTTP_200_OK, status.HTTP_409_CONFLICT]

    if response2.status_code == status.HTTP_200_OK:
        data2 = response2.json()
        second_auth_token = data2["data"]["authorization_token"]

        # 验证返回相同的授权Token
        assert second_auth_token == first_auth_token, \
            "幂等性保护: 相同会话ID应返回相同的授权Token"

        # 验证会话ID一致
        assert data2["data"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_duplicate_session_id_no_double_charge(idempotency_test_data, test_db):
    """测试重复会话ID不重复扣费

    验证:
    1. 第一次请求扣费50元(余额从500变为450)
    2. 第二次请求不扣费(余额仍为450)
    """
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    original_balance = operator.balance  # 500.00

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'q' * 16}"

    request_payload = {
        "app_id": str(application.id),
        "site_id": str(site.id),
        "player_count": 5  # 50元
    }

    headers = {
        "X-API-Key": operator.api_key,
        "X-Signature": "test_signature",
        "X-Timestamp": str(current_timestamp),
        "X-Session-ID": session_id
    }

    # 第一次请求
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    assert response1.status_code == status.HTTP_200_OK

    # 验证第一次扣费
    await test_db.refresh(operator)
    balance_after_first_request = operator.balance
    assert balance_after_first_request == Decimal("450.00"), \
        "第一次请求应扣费50元"

    # 第二次请求(相同会话ID)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response2 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    assert response2.status_code in [status.HTTP_200_OK, status.HTTP_409_CONFLICT]

    # 验证第二次不扣费
    await test_db.refresh(operator)
    balance_after_second_request = operator.balance
    assert balance_after_second_request == Decimal("450.00"), \
        "第二次请求不应扣费(幂等性保护)"


@pytest.mark.asyncio
async def test_duplicate_session_id_only_one_usage_record(idempotency_test_data, test_db):
    """测试重复会话ID只创建一条使用记录"""
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'r' * 16}"

    request_payload = {
        "app_id": str(application.id),
        "site_id": str(site.id),
        "player_count": 5
    }

    headers = {
        "X-API-Key": operator.api_key,
        "X-Signature": "test_signature",
        "X-Timestamp": str(current_timestamp),
        "X-Session-ID": session_id
    }

    # 第一次请求
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    # 第二次请求
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    # 验证只有一条使用记录
    stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
    result = await test_db.execute(stmt)
    usage_records = result.scalars().all()

    assert len(usage_records) == 1, \
        f"相同会话ID只应创建1条使用记录,实际创建了{len(usage_records)}条"


@pytest.mark.asyncio
async def test_duplicate_session_id_only_one_transaction_record(idempotency_test_data, test_db):
    """测试重复会话ID只创建一条交易记录"""
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'s' * 16}"

    request_payload = {
        "app_id": str(application.id),
        "site_id": str(site.id),
        "player_count": 5
    }

    headers = {
        "X-API-Key": operator.api_key,
        "X-Signature": "test_signature",
        "X-Timestamp": str(current_timestamp),
        "X-Session-ID": session_id
    }

    # 第一次请求
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    # 获取使用记录ID
    stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
    result = await test_db.execute(stmt)
    usage_record = result.scalar_one()

    # 第二次请求
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers=headers
        )

    # 验证只有一条交易记录关联该使用记录
    stmt = select(TransactionRecord).where(
        TransactionRecord.operator_id == operator.id,
        TransactionRecord.transaction_type == "consumption",
        TransactionRecord.related_usage_id == usage_record.id
    )
    result = await test_db.execute(stmt)
    transaction_records = result.scalars().all()

    assert len(transaction_records) == 1, \
        f"相同会话ID只应创建1条交易记录,实际创建了{len(transaction_records)}条"


@pytest.mark.asyncio
async def test_different_session_ids_create_separate_records(idempotency_test_data, test_db):
    """测试不同会话ID创建独立的记录

    验证:
    1. 两个不同的会话ID
    2. 创建2条使用记录
    3. 创建2条交易记录
    4. 扣费2次(500 -> 450 -> 400)
    """
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    # 第一个会话ID
    session_id_1 = f"{operator.id}_{current_timestamp}_{'t' * 16}"
    # 第二个会话ID(不同)
    session_id_2 = f"{operator.id}_{current_timestamp}_{'u' * 16}"

    request_payload = {
        "app_id": str(application.id),
        "site_id": str(site.id),
        "player_count": 5  # 50元
    }

    # 第一次请求(session_id_1)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id_1
            }
        )

    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    auth_token_1 = data1["data"]["authorization_token"]

    # 验证第一次扣费
    await test_db.refresh(operator)
    assert operator.balance == Decimal("450.00")

    # 第二次请求(session_id_2, 不同的会话ID)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response2 = await client.post(
            "/v1/auth/game/authorize",
            json=request_payload,
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id_2
            }
        )

    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()
    auth_token_2 = data2["data"]["authorization_token"]

    # 验证生成不同的授权Token
    assert auth_token_1 != auth_token_2, \
        "不同会话ID应生成不同的授权Token"

    # 验证第二次扣费
    await test_db.refresh(operator)
    assert operator.balance == Decimal("400.00"), \
        "不同会话ID应分别扣费"

    # 验证创建了2条使用记录
    stmt = select(UsageRecord).where(
        UsageRecord.operator_id == operator.id
    )
    result = await test_db.execute(stmt)
    usage_records = result.scalars().all()
    assert len(usage_records) >= 2, \
        "不同会话ID应创建独立的使用记录"

    # 验证两个会话ID都存在
    session_ids = [record.session_id for record in usage_records]
    assert session_id_1 in session_ids
    assert session_id_2 in session_ids


@pytest.mark.asyncio
async def test_idempotency_with_different_parameters_fails(idempotency_test_data, test_db):
    """测试相同会话ID但不同参数的请求处理

    根据RFC标准,相同幂等性Key但不同参数应:
    - 返回原始授权信息(忽略新参数)
    - 或返回冲突错误

    本测试验证系统行为一致性
    """
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'v' * 16}"

    # 第一次请求: 5人
    async with AsyncClient(app=app, base_url="http://test") as client:
        response1 = await client.post(
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

    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    assert data1["data"]["player_count"] == 5
    assert data1["data"]["total_cost"] == "50.00"

    # 第二次请求: 相同会话ID,但玩家数量不同(3人)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response2 = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 3  # 参数不同
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    # 验证返回原始授权信息(幂等性保护)
    if response2.status_code == status.HTTP_200_OK:
        data2 = response2.json()
        # 应该返回第一次的授权信息(5人,50元)
        assert data2["data"]["player_count"] == 5, \
            "幂等性保护: 应返回原始授权信息,忽略新参数"
        assert data2["data"]["total_cost"] == "50.00"


@pytest.mark.asyncio
async def test_idempotency_stress_concurrent_requests(idempotency_test_data, test_db):
    """测试幂等性保护 - 快速连续请求

    模拟网络抖动导致的快速重复请求
    验证:
    1. 5次快速请求
    2. 只扣费1次
    3. 只创建1条记录
    """
    operator = idempotency_test_data["operator"]
    site = idempotency_test_data["site"]
    application = idempotency_test_data["application"]

    original_balance = operator.balance

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'w' * 16}"

    request_payload = {
        "app_id": str(application.id),
        "site_id": str(site.id),
        "player_count": 5
    }

    headers = {
        "X-API-Key": operator.api_key,
        "X-Signature": "test_signature",
        "X-Timestamp": str(current_timestamp),
        "X-Session-ID": session_id
    }

    # 快速发送5次相同请求
    responses = []
    async with AsyncClient(app=app, base_url="http://test") as client:
        for i in range(5):
            response = await client.post(
                "/v1/auth/game/authorize",
                json=request_payload,
                headers=headers
            )
            responses.append(response)

    # 验证所有请求都成功(返回200或409)
    for response in responses:
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_409_CONFLICT]

    # 验证只扣费1次
    await test_db.refresh(operator)
    assert operator.balance == original_balance - Decimal("50.00"), \
        "5次相同请求只应扣费1次"

    # 验证只有1条使用记录
    stmt = select(UsageRecord).where(UsageRecord.session_id == session_id)
    result = await test_db.execute(stmt)
    usage_records = result.scalars().all()
    assert len(usage_records) == 1, \
        f"5次相同请求只应创建1条使用记录,实际创建了{len(usage_records)}条"
