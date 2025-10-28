"""
契约测试：运营商充值接口 (T052)

测试目标:
- 验证 POST /v1/operators/me/recharge 接口契约
- 确保请求/响应格式符合 OpenAPI 契约定义 (operator.yaml L264-340)
- 覆盖微信/支付宝支付方式、金额边界、认证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 请求体包含 amount (10-10000元) 和 payment_method (wechat/alipay)
- 返回201创建成功，包含订单ID、支付二维码URL、过期时间
"""
import pytest
from httpx import AsyncClient
from decimal import Decimal

from src.main import app


# ========== 辅助函数 ==========

async def create_and_login_operator(client: AsyncClient, username: str) -> str:
    """创建运营商并登录,返回JWT Token"""
    # 注册
    await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "测试公司",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )

    # 登录
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return response.json()["data"]["access_token"]


# ========== POST /v1/operators/me/recharge 成功场景 ==========

@pytest.mark.asyncio
async def test_recharge_wechat_success(test_db):
    """测试微信充值成功"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_wechat_user")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "500.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证success字段
    assert data["success"] is True

    # 验证data结构
    assert "data" in data
    order_data = data["data"]

    # 验证必需字段
    required_fields = ["order_id", "amount", "payment_method", "qr_code_url", "expires_at"]
    for field in required_fields:
        assert field in order_data, f"缺少必需字段: {field}"

    # 验证字段值
    assert order_data["amount"] == "500.00"
    assert order_data["payment_method"] == "wechat"
    assert order_data["order_id"].startswith("ord_recharge_")
    assert order_data["qr_code_url"].startswith("http")


@pytest.mark.asyncio
async def test_recharge_alipay_success(test_db):
    """测试支付宝充值成功"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_alipay_user")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "1000.00",
                "payment_method": "alipay"
            }
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["payment_method"] == "alipay"
    assert data["amount"] == "1000.00"


@pytest.mark.asyncio
async def test_recharge_minimum_amount(test_db):
    """测试最小充值金额 (10元)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_min_user")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "10.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["amount"] == "10.00"


@pytest.mark.asyncio
async def test_recharge_maximum_amount(test_db):
    """测试最大充值金额 (10000元)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_max_user")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "10000.00",
                "payment_method": "alipay"
            }
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["amount"] == "10000.00"


# ========== 金额边界和格式测试 ==========

@pytest.mark.asyncio
async def test_recharge_amount_below_minimum(test_db):
    """测试低于最小金额 (< 10元) 应失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_below_min")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "9.99",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_recharge_amount_above_maximum(test_db):
    """测试超过最大金额 (> 10000元) 应失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_above_max")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "10000.01",
                "payment_method": "alipay"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_recharge_amount_zero(test_db):
    """测试零金额应失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_zero_user")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "0.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_recharge_amount_negative(test_db):
    """测试负金额应失败"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_negative")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "-50.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_recharge_amount_invalid_format(test_db):
    """测试金额格式错误 (超过2位小数)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_format_user")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.123",  # 3位小数
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 400


# ========== 支付方式测试 ==========

@pytest.mark.asyncio
async def test_recharge_invalid_payment_method(test_db):
    """测试无效支付方式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_invalid_method")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00",
                "payment_method": "bank_transfer"  # 不支持的方式
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_recharge_missing_payment_method(test_db):
    """测试缺少支付方式字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_missing_method")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "100.00"
                # payment_method缺失
            }
        )

    assert response.status_code == 400


# ========== 认证授权测试 ==========

@pytest.mark.asyncio
async def test_recharge_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/recharge",
            json={
                "amount": "100.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 401
    data = response.json()
    assert "error_code" in data


@pytest.mark.asyncio
async def test_recharge_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json={
                "amount": "100.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 401


# ========== 响应格式完整性测试 ==========

@pytest.mark.asyncio
async def test_recharge_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_format_check")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "amount": "500.00",
                "payment_method": "wechat"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证顶层结构
    assert "success" in data
    assert "data" in data
    assert isinstance(data["success"], bool)
    assert data["success"] is True

    # 验证order_data类型
    order_data = data["data"]
    assert isinstance(order_data["order_id"], str)
    assert isinstance(order_data["amount"], str)
    assert isinstance(order_data["payment_method"], str)
    assert isinstance(order_data["qr_code_url"], str)
    assert isinstance(order_data["expires_at"], str)

    # 验证枚举值
    assert order_data["payment_method"] in ["wechat", "alipay"]

    # 验证URL格式
    assert order_data["qr_code_url"].startswith("http")

    # 验证时间格式 (ISO 8601)
    from datetime import datetime
    try:
        datetime.fromisoformat(order_data["expires_at"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"expires_at时间格式错误: {order_data['expires_at']}")


@pytest.mark.asyncio
async def test_recharge_order_id_uniqueness(test_db):
    """测试订单ID唯一性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "recharge_unique_user")

        # 发起两次充值
        response1 = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": "100.00", "payment_method": "wechat"}
        )

        response2 = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": "200.00", "payment_method": "alipay"}
        )

    assert response1.status_code == 201
    assert response2.status_code == 201

    order_id_1 = response1.json()["data"]["order_id"]
    order_id_2 = response2.json()["data"]["order_id"]

    # 验证订单ID不同
    assert order_id_1 != order_id_2


# ========== 缺失必需字段测试 ==========

@pytest.mark.asyncio
async def test_recharge_missing_amount(test_db):
    """测试缺少amount字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_missing_amt")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "payment_method": "wechat"
                # amount缺失
            }
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_recharge_empty_request_body(test_db):
    """测试空请求体"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "rch_empty_body")

        response = await client.post(
            "/v1/operators/me/recharge",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

    assert response.status_code == 400
