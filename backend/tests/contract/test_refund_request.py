"""
契约测试: 退款申请接口 (T074)

测试目标:
- 验证 POST /v1/operators/me/refunds 接口契约
- 确保请求/响应格式符合contract定义
- 覆盖正常申请、余额为0、参数验证场景

契约要求:
- 需要JWT Token认证 (Authorization: Bearer {token})
- 请求体: reason (10-500字符)
- 返回格式: {success: true, message: str, data: RefundRequest}
- 余额为0时返回400错误
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

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


async def set_operator_balance(db, operator_id: str, balance: float):
    """直接设置运营商余额(用于测试)"""
    from src.models.operator import OperatorAccount
    from sqlalchemy import select
    from uuid import UUID

    # 解析operator_id
    if operator_id.startswith("op_"):
        uuid_str = operator_id[3:]
    else:
        uuid_str = operator_id

    stmt = select(OperatorAccount).where(OperatorAccount.id == UUID(uuid_str))
    result = await db.execute(stmt)
    operator = result.scalar_one_or_none()

    if operator:
        operator.balance = balance
        await db.commit()


# ========== POST /v1/operators/me/refunds 测试 ==========

@pytest.mark.asyncio
async def test_apply_refund_success(test_db):
    """测试成功申请退款"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_1")

        # 设置余额为500元
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await set_operator_balance(test_db, operator_id, 500.00)

        # 申请退款
        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "业务调整，不再继续使用服务"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证响应结构
    assert data["success"] is True
    assert "message" in data
    assert "data" in data

    # 验证退款申请数据
    refund = data["data"]
    assert "refund_id" in refund
    assert refund["refund_id"].startswith("refund_")
    assert refund["requested_amount"] == "500.00"
    assert refund["status"] == "pending"
    assert refund["reason"] == "业务调整，不再继续使用服务"
    assert "created_at" in refund


@pytest.mark.asyncio
async def test_apply_refund_zero_balance(test_db):
    """测试余额为0时申请退款"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_2")

        # 余额默认为0
        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "业务调整，不再继续使用服务"
            }
        )

    assert response.status_code == 400
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "INVALID_PARAMS"


@pytest.mark.asyncio
async def test_apply_refund_without_token(test_db):
    """测试未提供Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/refunds",
            json={
                "reason": "业务调整，不再继续使用服务"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_apply_refund_with_invalid_token(test_db):
    """测试无效Token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": "Bearer invalid_token_12345"},
            json={
                "reason": "业务调整，不再继续使用服务"
            }
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_apply_refund_reason_too_short(test_db):
    """测试退款原因太短(小于10字符)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_3")

        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "太短了"  # 只有3个字符
            }
        )

    assert response.status_code == 400  # Pydantic validation error (系统统一返回400)


@pytest.mark.asyncio
async def test_apply_refund_reason_too_long(test_db):
    """测试退款原因太长(超过500字符)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_4")

        # 生成501字符的原因
        long_reason = "x" * 501

        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": long_reason
            }
        )

    assert response.status_code == 400  # Pydantic validation error (系统统一返回400)


@pytest.mark.asyncio
async def test_apply_refund_missing_reason(test_db):
    """测试缺少reason字段"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_5")

        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )

    assert response.status_code == 400  # Pydantic validation error (系统统一返回400)


@pytest.mark.asyncio
async def test_apply_refund_response_format(test_db):
    """测试响应格式的完整性"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_6")

        # 设置余额
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await set_operator_balance(test_db, operator_id, 100.00)

        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "测试退款申请的响应格式验证"
            }
        )

    assert response.status_code == 201
    data = response.json()

    # 验证顶层格式
    assert isinstance(data["success"], bool)
    assert data["success"] is True
    assert isinstance(data["message"], str)
    assert isinstance(data["data"], dict)

    # 验证data内部结构
    refund = data["data"]
    assert isinstance(refund["refund_id"], str)
    assert isinstance(refund["requested_amount"], str)
    assert isinstance(refund["status"], str)
    assert isinstance(refund["reason"], str)
    assert isinstance(refund["created_at"], str)

    # 验证可选字段(首次申请时应为None)
    assert refund.get("actual_refund_amount") is None
    assert refund.get("reject_reason") is None
    assert refund.get("reviewed_by") is None
    assert refund.get("reviewed_at") is None


@pytest.mark.asyncio
async def test_apply_refund_multiple_times(test_db):
    """测试多次申请退款(验证是否允许重复申请)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_7")

        # 设置余额
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await set_operator_balance(test_db, operator_id, 200.00)

        # 第一次申请
        response1 = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "第一次申请退款的原因说明"
            }
        )

        # 第二次申请
        response2 = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "第二次申请退款的原因说明"
            }
        )

    # 两次申请都应该成功(业务规则允许多次申请)
    assert response1.status_code == 201
    assert response2.status_code == 201

    # 验证两次申请的refund_id不同
    refund_id_1 = response1.json()["data"]["refund_id"]
    refund_id_2 = response2.json()["data"]["refund_id"]
    assert refund_id_1 != refund_id_2


@pytest.mark.asyncio
async def test_apply_refund_refund_id_format(test_db):
    """测试refund_id格式"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "refund_user_8")

        # 设置余额
        from src.core.security.jwt import verify_token
        payload = verify_token(token)
        operator_id = payload["sub"]
        await set_operator_balance(test_db, operator_id, 150.00)

        response = await client.post(
            "/v1/operators/me/refunds",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": "验证退款ID格式的测试用例"
            }
        )

    assert response.status_code == 201
    refund_id = response.json()["data"]["refund_id"]

    # 验证格式: refund_<uuid>
    assert refund_id.startswith("refund_")
    assert len(refund_id) > 7  # "refund_" + UUID部分
