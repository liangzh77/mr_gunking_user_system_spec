r"""集成测试：会话ID格式验证 (T033a - FR-061)

测试FR-061需求 - 会话ID格式验证:

格式规范: {operatorId}_{timestamp}_{random16}
- operatorId: 运营商UUID字符串
- timestamp: Unix时间戳(秒)
- random16: 16位随机字符串(字母数字)

验证项:
1. 格式必须匹配正则: ^[a-zA-Z0-9\-]+_\d+_[a-zA-Z0-9]{16}$
2. operatorId必须与请求的运营商匹配
3. timestamp不能超过5分钟前
4. random部分必须恰好16字符
5. 无效格式返回HTTP 400
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
async def session_id_test_data(test_db):
    """准备会话ID测试数据"""
    # 创建管理员
    admin = AdminAccount(
        username="admin_session_id",
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
        username="op_session_id_001",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="j" * 64,
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
        name="会话ID测试运营点",
        address="测试地址",
        server_identifier="server_session_id_001",
        is_active=True
    )
    test_db.add(site)
    await test_db.flush()

    # 创建应用
    application = Application(
        app_code="app_session_id_001",
        app_name="会话ID测试游戏",
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
async def test_session_id_valid_format_success(session_id_test_data):
    """测试有效的会话ID格式成功授权

    格式: {operatorId}_{timestamp}_{random16}
    示例: 550e8400-e29b-41d4-a716-446655440000_1704067200_a1b2c3d4e5f6g7h8
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())
    valid_session_id = f"{operator.id}_{current_timestamp}_{'a' * 16}"

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
                "X-Session-ID": valid_session_id
            }
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_session_id_invalid_format_fails(session_id_test_data):
    """测试无效格式的会话ID被拒绝

    无效格式示例:
    - "invalid_format" (不符合三段式)
    - "test_12345" (缺少random部分)
    - "op_test_abc_xyz" (时间戳不是数字)
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    invalid_session_ids = [
        "invalid_format",  # 不符合三段式
        "test_12345",  # 缺少random部分
        "op_test_abc_xyz",  # 时间戳不是数字
        "op_test_12345_short",  # random部分不足16字符
        "op test_12345_" + "a" * 16,  # 包含空格
        "",  # 空字符串
    ]

    for invalid_session_id in invalid_session_ids:
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
                    "X-Session-ID": invalid_session_id
                }
            )

        # 应返回400错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED  # 如果API Key验证先执行可能返回401
        ], f"无效会话ID格式应被拒绝: {invalid_session_id}"

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            data = response.json()
            assert data["detail"]["error_code"] in [
                "INVALID_SESSION_ID_FORMAT",
                "INVALID_SESSION_ID"
            ]


@pytest.mark.asyncio
async def test_session_id_operator_mismatch_fails(session_id_test_data, test_db):
    """测试会话ID中的operatorId与请求运营商不匹配

    场景:
    - 运营商A的API Key
    - 会话ID包含运营商B的ID
    - 预期: HTTP 400 错误
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]
    admin = session_id_test_data["admin"]

    # 创建另一个运营商
    another_operator = OperatorAccount(
        username="op_another_session_id",
        full_name="Test Operator",
        email="operator@test.com",
        phone="13900139000",
        password_hash="hashed_password",
        api_key="k" * 64,
        api_key_hash="hashed_secret",
        balance=Decimal("300.00"),
        customer_tier="standard",
        is_active=True,
        is_locked=False,
        created_by=admin.id
    )
    test_db.add(another_operator)
    await test_db.commit()

    current_timestamp = int(datetime.utcnow().timestamp())

    # 使用operator的API Key,但会话ID包含another_operator的ID
    mismatched_session_id = f"{another_operator.id}_{current_timestamp}_{'b' * 16}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": str(application.id),
                "site_id": str(site.id),
                "player_count": 5
            },
            headers={
                "X-API-Key": operator.api_key,  # operator的API Key
                "X-Signature": "test_signature",
                "X-Timestamp": str(current_timestamp),
                "X-Session-ID": mismatched_session_id  # 但会话ID属于another_operator
            }
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"]["error_code"] in [
        "SESSION_ID_OPERATOR_MISMATCH",
        "INVALID_SESSION_ID"
    ]


@pytest.mark.asyncio
async def test_session_id_expired_timestamp_fails(session_id_test_data):
    """测试过期的时间戳(超过5分钟)被拒绝

    场景:
    - 时间戳是6分钟前(超过5分钟限制)
    - 预期: HTTP 400 错误
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    # 6分钟前的时间戳(超过5分钟限制)
    expired_timestamp = int((datetime.utcnow() - timedelta(minutes=6)).timestamp())
    expired_session_id = f"{operator.id}_{expired_timestamp}_{'c' * 16}"

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
                "X-Timestamp": str(int(datetime.utcnow().timestamp())),
                "X-Session-ID": expired_session_id
            }
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"]["error_code"] in [
        "SESSION_ID_EXPIRED",
        "INVALID_SESSION_ID"
    ]


@pytest.mark.asyncio
async def test_session_id_within_5_minutes_success(session_id_test_data):
    """测试5分钟内的时间戳成功授权

    边界测试:
    - 4分59秒前的时间戳(在5分钟限制内)
    - 预期: HTTP 200 OK
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    # 4分59秒前的时间戳(在5分钟限制内)
    recent_timestamp = int((datetime.utcnow() - timedelta(seconds=299)).timestamp())
    recent_session_id = f"{operator.id}_{recent_timestamp}_{'d' * 16}"

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
                "X-Timestamp": str(int(datetime.utcnow().timestamp())),
                "X-Session-ID": recent_session_id
            }
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_session_id_random_part_length_validation(session_id_test_data):
    """测试random部分长度验证

    验证:
    - 15字符: 失败
    - 16字符: 成功
    - 17字符: 失败
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    # 测试15字符(不足)
    session_id_15 = f"{operator.id}_{current_timestamp}_{'e' * 15}"

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
                "X-Session-ID": session_id_15
            }
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, \
        "random部分15字符应被拒绝"

    # 测试16字符(正确)
    session_id_16 = f"{operator.id}_{current_timestamp}_{'f' * 16}"

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
                "X-Session-ID": session_id_16
            }
        )

    assert response.status_code == status.HTTP_200_OK, \
        "random部分16字符应该成功"

    # 测试17字符(超长)
    session_id_17 = f"{operator.id}_{current_timestamp}_{'g' * 17}"

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
                "X-Session-ID": session_id_17
            }
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST, \
        "random部分17字符应被拒绝"


@pytest.mark.asyncio
async def test_session_id_future_timestamp_allowed(session_id_test_data):
    """测试未来的时间戳(合理范围内)

    场景:
    - 时间戳是1分钟后(考虑时钟偏差)
    - 根据业务需求,可能允许或拒绝
    - 本测试记录实际行为
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    # 1分钟后的时间戳
    future_timestamp = int((datetime.utcnow() + timedelta(minutes=1)).timestamp())
    future_session_id = f"{operator.id}_{future_timestamp}_{'h' * 16}"

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
                "X-Timestamp": str(int(datetime.utcnow().timestamp())),
                "X-Session-ID": future_session_id
            }
        )

    # 根据实现可能接受或拒绝未来时间戳
    # 这里记录实际行为
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        data = response.json()
        assert data["detail"]["error_code"] in [
            "SESSION_ID_FUTURE_TIMESTAMP",
            "INVALID_SESSION_ID"
        ]
    else:
        # 如果允许未来时间戳,应该成功
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_session_id_special_characters_in_random(session_id_test_data):
    """测试random部分包含特殊字符

    允许: 字母数字 [a-zA-Z0-9]
    不允许: 特殊字符 (-, _, @, #, 等)
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    # random部分包含特殊字符
    invalid_random_parts = [
        "abcd1234-efgh567",  # 包含连字符
        "abcd1234_efgh567",  # 包含下划线
        "abcd1234@efgh567",  # 包含@
        "abcd1234#efgh567",  # 包含#
        "abcd 1234 efgh56",  # 包含空格
    ]

    for invalid_random in invalid_random_parts:
        assert len(invalid_random) == 16, "测试数据错误:random部分必须16字符"

        session_id = f"{operator.id}_{current_timestamp}_{invalid_random}"

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

        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"random部分包含特殊字符应被拒绝: {invalid_random}"


@pytest.mark.asyncio
async def test_session_id_alphanumeric_combinations(session_id_test_data):
    """测试各种有效的字母数字组合

    验证random部分可以是:
    - 纯字母
    - 纯数字
    - 字母数字混合
    """
    operator = session_id_test_data["operator"]
    site = session_id_test_data["site"]
    application = session_id_test_data["application"]

    current_timestamp = int(datetime.utcnow().timestamp())

    valid_random_parts = [
        "a" * 16,  # 纯小写字母
        "A" * 16,  # 纯大写字母
        "1" * 16,  # 纯数字
        "aA1bB2cC3dD4eE5f",  # 混合
        "1a2b3c4d5e6f7g8h",  # 数字开头混合
    ]

    for i, valid_random in enumerate(valid_random_parts):
        assert len(valid_random) == 16, f"测试数据错误:random部分必须16字符: {valid_random}"

        # 每次使用不同的时间戳以避免幂等性冲突
        session_id = f"{operator.id}_{current_timestamp + i}_{valid_random}"

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

        assert response.status_code == status.HTTP_200_OK, \
            f"有效的random部分应该成功: {valid_random}"
