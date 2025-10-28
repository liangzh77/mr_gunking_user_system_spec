"""集成测试：玩家数量范围验证 (T033)

测试玩家数量验证逻辑:
1. 验证最小值限制(min_players)
2. 验证最大值限制(max_players)
3. 验证应用级别的玩家范围配置
4. 验证边界值(最小值-1, 最小值, 最大值, 最大值+1)
5. 验证非法值(0, 负数, 超大值)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from httpx import AsyncClient
from fastapi import status

from src.main import app
from src.models.admin import AdminAccount
from src.models.operator import OperatorAccount
from src.models.application import Application
from src.models.site import OperationSite
from src.models.authorization import OperatorAppAuthorization


@pytest.fixture
async def player_count_test_data(test_db):
    """准备玩家数量测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_player_count",
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
        username="op_player_count_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="h" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("1000.00"),  # 充足余额
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
        name="玩家数量测试运营点",
        address="测试地址",
        server_identifier="server_player_count_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用 - 2-8人游戏
    application = Application(
        app_code="app_player_count_001",
        app_name="2-8人游戏",
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
async def test_player_count_within_range_success(player_count_test_data):
    """测试玩家数量在范围内(2-8人)成功授权"""
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    # 测试有效值: 2, 5, 8
    valid_counts = [2, 5, 8]

    for player_count in valid_counts:
        current_timestamp = int(datetime.utcnow().timestamp())
        session_id = f"{operator.id}_{current_timestamp}_{player_count:016d}"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/game/authorize",
                json={
                    "app_id": str(application.id),
                    "site_id": str(site.id),
                    "player_count": player_count
                },
                headers={
                    "X-API-Key": operator.api_key,
                    "X-Signature": "test_signature",
                    "X-Timestamp": str(current_timestamp),
                    "X-Session-ID": session_id
                }
            )

        assert response.status_code == status.HTTP_200_OK, \
            f"玩家数量{player_count}应该通过验证(范围2-8)"

        data = response.json()
        assert data["data"]["player_count"] == player_count


@pytest.mark.asyncio
async def test_player_count_below_minimum_fails(player_count_test_data):
    """测试玩家数量低于最小值(< 2人)失败"""
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    # 测试无效值: 0, 1
    invalid_counts = [0, 1]

    for player_count in invalid_counts:
        current_timestamp = int(datetime.utcnow().timestamp())
        session_id = f"{operator.id}_{current_timestamp}_{'x' * 16}"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/game/authorize",
                json={
                    "app_id": str(application.id),
                    "site_id": str(site.id),
                    "player_count": player_count
                },
                headers={
                    "X-API-Key": operator.api_key,
                    "X-Signature": "test_signature",
                    "X-Timestamp": str(current_timestamp),
                    "X-Session-ID": session_id
                }
            )

        # 应返回400或422错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ], f"玩家数量{player_count}应该被拒绝(最小值2)"

        data = response.json()
        if "detail" in data and isinstance(data["detail"], dict):
            assert data["detail"]["error_code"] in [
                "PLAYER_COUNT_OUT_OF_RANGE",
                "INVALID_PLAYER_COUNT"
            ]


@pytest.mark.asyncio
async def test_player_count_above_maximum_fails(player_count_test_data):
    """测试玩家数量超过最大值(> 8人)失败"""
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    # 测试无效值: 9, 10, 20
    invalid_counts = [9, 10, 20]

    for player_count in invalid_counts:
        current_timestamp = int(datetime.utcnow().timestamp())
        session_id = f"{operator.id}_{current_timestamp}_{'y' * 16}"

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/v1/auth/game/authorize",
                json={
                    "app_id": str(application.id),
                    "site_id": str(site.id),
                    "player_count": player_count
                },
                headers={
                    "X-API-Key": operator.api_key,
                    "X-Signature": "test_signature",
                    "X-Timestamp": str(current_timestamp),
                    "X-Session-ID": session_id
                }
            )

        # 应返回400错误
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"玩家数量{player_count}应该被拒绝(最大值8)"

        data = response.json()
        assert data["detail"]["error_code"] in [
            "PLAYER_COUNT_OUT_OF_RANGE",
            "INVALID_PLAYER_COUNT"
        ]


@pytest.mark.asyncio
async def test_player_count_negative_value_fails(player_count_test_data):
    """测试负数玩家数量失败"""
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'z' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": -5  # 负数
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    # Pydantic验证应该在API层拦截
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ], "负数玩家数量应该被拒绝"


@pytest.mark.asyncio
async def test_player_count_boundary_minimum_exact(player_count_test_data):
    """测试边界值 - 恰好等于最小值(2人)"""
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'1' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 2  # 恰好等于最小值
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
async def test_player_count_boundary_maximum_exact(player_count_test_data):
    """测试边界值 - 恰好等于最大值(8人)"""
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'2' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 8  # 恰好等于最大值
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
async def test_player_count_different_app_ranges(test_db):
    """测试不同应用的玩家范围配置

    创建:
    - 应用A: 1-4人游戏
    - 应用B: 4-12人游戏
    验证范围独立生效
    """
    # 创建管理员
    admin = AdminAccount(
        username="admin_multi_range",
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
        username="op_multi_range_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="i" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("1000.00"),
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
        name="多范围测试运营点",
        address="测试地址",
        server_identifier="server_multi_range_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 应用A: 1-4人游戏
    app_a = Application(
        app_code="app_1_to_4_players",
        app_name="1-4人小游戏",
        price_per_player=Decimal("5.00"),
        min_players=1,
        max_players=4,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(app_a)
    await test_db.flush()

    # 应用B: 4-12人游戏
    app_b = Application(
        app_code="app_4_to_12_players",
        app_name="4-12人大游戏",
        price_per_player=Decimal("15.00"),
        min_players=4,
        max_players=12,
        is_active=True,
        created_by=admin.id
    )
    test_db.add(app_b)
    await test_db.flush()

    # 创建授权关系
    auth_a = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=app_a.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(auth_a)

    auth_b = OperatorAppAuthorization(
        operator_id=operator.id,
        application_id=app_b.id,
        authorized_by=admin.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )
    test_db.add(auth_b)
    await test_db.commit()

    # 测试应用A: 3人应该成功(在1-4范围内)
    current_timestamp = int(datetime.utcnow().timestamp())
    session_id_a = f"{operator.id}_{current_timestamp}_{'3' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response_a = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(app_a.id),
                "site_id": str(site.id),
                "player_count": 3
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id_a
            }
        )

    assert response_a.status_code == status.HTTP_200_OK
    assert response_a.json()["data"]["player_count"] == 3

    # 测试应用B: 3人应该失败(最小值4)
    session_id_b1 = f"{operator.id}_{current_timestamp}_{'4' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response_b1 = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(app_b.id),
                "site_id": str(site.id),
                "player_count": 3
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id_b1
            }
        )

    assert response_b1.status_code == status.HTTP_400_BAD_REQUEST

    # 测试应用B: 10人应该成功(在4-12范围内)
    session_id_b2 = f"{operator.id}_{current_timestamp}_{'5' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response_b2 = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(app_b.id),
                "site_id": str(site.id),
                "player_count": 10
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id_b2
            }
        )

    assert response_b2.status_code == status.HTTP_200_OK
    assert response_b2.json()["data"]["player_count"] == 10

    # 测试应用A: 10人应该失败(最大值4)
    session_id_a2 = f"{operator.id}_{current_timestamp}_{'6' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response_a2 = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(app_a.id),
                "site_id": str(site.id),
                "player_count": 10
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id_a2
            }
        )

    assert response_a2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_player_count_pydantic_validation(player_count_test_data):
    """测试Pydantic层的玩家数量验证

    根据contracts/auth.yaml:
    - minimum: 1
    - maximum: 100

    这是API层的通用限制,应用层可以有更严格的限制
    """
    operator = player_count_test_data["operator"]
    site = player_count_test_data["site"]
    application = player_count_test_data["application"]

    # 测试超过Pydantic限制(> 100)
    current_timestamp = int(datetime.utcnow().timestamp())
    session_id = f"{operator.id}_{current_timestamp}_{'7' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 101  # 超过API层限制
            },
            headers={
                "X-API-Key": operator.api_key,
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": session_id
            }
        )

    # 应该被Pydantic拦截(422)或业务逻辑拒绝(400)
    assert response.status_code in [
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ]
