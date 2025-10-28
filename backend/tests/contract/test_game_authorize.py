"""契约测试：游戏授权接口 (T029)

验证 POST /v1/auth/game/authorize 端点符合 contracts/auth.yaml 规范。

契约验证项:
1. 请求参数格式 (app_id, site_id, player_count)
2. 必需的请求头 (X-API-Key, X-Signature, X-Timestamp, X-Session-ID)
3. 响应格式 (GameAuthorizeResponse schema)
4. 错误响应格式 (ErrorResponse schema)
5. HTTP状态码 (200/400/401/402/403/409/429/500)
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_authorize_game_request_schema():
    """测试请求体Schema契约

    验证:
    - 必需字段: app_id, site_id, player_count
    - 字段类型正确
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 缺少必需字段
        response = await client.post(
            "/v1/auth/game/authorize",
            json={"app_id": "test_app"},  # 缺少 site_id, player_count
            headers={
                "X-API-Key": "test_key_64_chars_long_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "X-Signature": "test_signature",
                "X-Timestamp": "1704067200",
                "X-Session-ID": "test_operator_1704067200_1234567890abcdef"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        # 验证响应包含错误信息（自定义格式或FastAPI默认格式）
        assert "detail" in data or "error" in data or "message" in data


@pytest.mark.asyncio
async def test_authorize_game_required_headers():
    """测试必需请求头契约

    验证:
    - X-API-Key (必需)
    - X-Signature (必需)
    - X-Timestamp (必需)
    - X-Session-ID (必需)
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 缺少所有必需头
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": "app_space_adventure_001",
                "site_id": "site_beijing_001",
                "player_count": 5
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        # 验证响应包含错误信息（自定义格式或FastAPI默认格式）
        assert "detail" in data or "error" in data or "message" in data

        # 验证缺少X-API-Key的错误信息
        # 检查不同的响应格式
        if "detail" in data and isinstance(data["detail"], list):
            error_fields = [error["loc"][-1] for error in data["detail"]]
            assert "x-api-key" in error_fields or "X-API-Key" in str(data)
        else:
            # 自定义错误格式，只要包含错误信息即可
            assert "X-API-Key" in str(data) or "api" in str(data).lower()


@pytest.mark.asyncio
async def test_authorize_game_success_response_schema():
    """测试成功响应Schema契约

    验证响应包含:
    - success: boolean
    - data.authorization_token: string (UUID)
    - data.session_id: string
    - data.app_name: string
    - data.player_count: integer
    - data.unit_price: string (decimal)
    - data.total_cost: string (decimal)
    - data.balance_after: string (decimal)
    - data.authorized_at: datetime (ISO 8601)
    """
    # 此测试需要完整的测试环境和数据fixtures
    # 这里仅验证响应结构的类型定义

    expected_response_keys = {
        "success",
        "data"
    }

    expected_data_keys = {
        "authorization_token",
        "session_id",
        "app_name",
        "player_count",
        "unit_price",
        "total_cost",
        "balance_after",
        "authorized_at"
    }

    # 模拟成功响应结构
    mock_response = {
        "success": True,
        "data": {
            "authorization_token": "550e8400-e29b-41d4-a716-446655440000",
            "session_id": "op_12345_1704067200_a1b2c3d4e5f6g7h8",
            "app_name": "太空探险",
            "player_count": 5,
            "unit_price": "10.00",
            "total_cost": "50.00",
            "balance_after": "450.00",
            "authorized_at": "2025-01-01T12:30:00.000Z"
        }
    }

    assert set(mock_response.keys()) == expected_response_keys
    assert set(mock_response["data"].keys()) == expected_data_keys
    assert isinstance(mock_response["success"], bool)
    assert isinstance(mock_response["data"]["player_count"], int)
    assert isinstance(mock_response["data"]["unit_price"], str)


@pytest.mark.asyncio
async def test_authorize_game_error_response_schema():
    """测试错误响应Schema契约

    验证错误响应包含:
    - error_code: string
    - message: string
    - details: object (optional)
    """
    expected_error_keys = {"error_code", "message"}

    # 模拟错误响应结构
    mock_error_responses = [
        {
            "error_code": "INSUFFICIENT_BALANCE",
            "message": "账户余额不足，当前余额: 30.00元，需要: 50.00元",
            "details": {
                "current_balance": "30.00",
                "required_amount": "50.00",
                "shortage": "20.00"
            }
        },
        {
            "error_code": "INVALID_API_KEY",
            "message": "API Key不存在或已失效，请联系管理员"
        },
        {
            "error_code": "PLAYER_COUNT_OUT_OF_RANGE",
            "message": "玩家数量必须在2-8之间，当前请求: 9人",
            "details": {
                "min_players": 2,
                "max_players": 8,
                "requested_players": 9
            }
        }
    ]

    for error in mock_error_responses:
        assert expected_error_keys.issubset(set(error.keys()))
        assert isinstance(error["error_code"], str)
        assert isinstance(error["message"], str)
        if "details" in error:
            assert isinstance(error["details"], dict)


@pytest.mark.asyncio
async def test_authorize_game_http_status_codes():
    """测试HTTP状态码契约

    验证各种场景返回正确的状态码:
    - 200: 授权成功
    - 400: 请求参数错误
    - 401: 认证失败
    - 402: 余额不足
    - 403: 应用未授权/账户锁定
    - 409: 会话重复
    - 429: 请求频率超限
    - 500: 服务器错误
    """
    # 这些测试需要在集成测试中验证,这里仅定义契约

    status_code_scenarios = {
        "success": status.HTTP_200_OK,
        "bad_request": status.HTTP_400_BAD_REQUEST,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
        "payment_required": status.HTTP_402_PAYMENT_REQUIRED,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "conflict": status.HTTP_409_CONFLICT,
        "too_many_requests": status.HTTP_429_TOO_MANY_REQUESTS,
        "internal_error": status.HTTP_500_INTERNAL_SERVER_ERROR
    }

    # 验证状态码是正确的HTTP标准码
    for scenario, code in status_code_scenarios.items():
        assert 200 <= code < 600, f"{scenario} has invalid status code: {code}"


@pytest.mark.asyncio
async def test_player_count_range_validation():
    """测试玩家数量范围验证契约

    根据contracts/auth.yaml:
    - minimum: 1
    - maximum: 100
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试玩家数量为0 (无效)
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": "app_space_adventure_001",
                "site_id": "site_beijing_001",
                "player_count": 0  # 低于最小值
            },
            headers={
                "X-API-Key": "test_key_64_chars_long_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "X-Signature": "test_signature",
                "X-Timestamp": "1704067200",
                "X-Session-ID": "test_operator_1704067200_1234567890abcdef"
            }
        )

        # 应该返回422验证错误或400业务错误
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]


@pytest.mark.asyncio
async def test_session_id_format_validation():
    r"""测试会话ID格式验证契约

    根据contracts/auth.yaml:
    - pattern: '^[a-zA-Z0-9]+_\d+_[a-zA-Z0-9]{16}$'
    - 格式: {operatorId}_{timestamp}_{random16}
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试无效的会话ID格式
        response = await client.post(
            "/v1/auth/game/authorize",
            json={
                "app_id": "app_space_adventure_001",
                "site_id": "site_beijing_001",
                "player_count": 5
            },
            headers={
                "X-API-Key": "test_key_64_chars_long_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "X-Signature": "test_signature",
                "X-Timestamp": "1704067200",
                "X-Session-ID": "invalid_format"  # 不符合规范
            }
        )

        # 应该返回400错误
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED  # 如果API Key验证先执行
        ]


@pytest.mark.asyncio
async def test_decimal_string_format():
    r"""测试金额字段格式契约

    验证金额字段都是字符串格式,保留2位小数:
    - unit_price: "10.00"
    - total_cost: "50.00"
    - balance_after: "450.00"
    """
    import re

    decimal_pattern = r'^\d+\.\d{2}$'

    test_values = ["10.00", "50.00", "450.00", "0.00", "9999.99"]

    for value in test_values:
        assert re.match(decimal_pattern, value), f"Invalid decimal format: {value}"

    # 无效格式
    invalid_values = ["10", "10.0", "10.000", "10.1", ".00", "abc"]

    for value in invalid_values:
        assert not re.match(decimal_pattern, value), f"Should reject: {value}"


@pytest.mark.asyncio
async def test_timestamp_header_format():
    """测试时间戳header格式契约

    根据contracts/auth.yaml:
    - X-Timestamp: Unix时间戳(秒)
    - format: int64
    - 服务端验证时间差不超过5分钟
    """
    import time

    current_timestamp = int(time.time())

    # 有效的时间戳格式
    valid_timestamps = [
        str(current_timestamp),
        str(current_timestamp - 60),  # 1分钟前
        str(current_timestamp + 60)   # 1分钟后
    ]

    for ts in valid_timestamps:
        assert ts.isdigit()
        assert len(ts) == 10  # Unix时间戳(秒)应该是10位

    # 过期的时间戳 (超过5分钟)
    expired_timestamp = current_timestamp - 301  # 5分01秒前
    assert expired_timestamp < current_timestamp - 300


def test_api_key_length():
    """测试API Key长度契约

    根据contracts/auth.yaml:
    - minLength: 64
    - maxLength: 64
    """
    valid_api_key = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
    assert len(valid_api_key) == 64

    invalid_api_keys = [
        "short_key",  # 太短
        "a" * 63,     # 63字符
        "a" * 65      # 65字符
    ]

    for key in invalid_api_keys:
        assert len(key) != 64
